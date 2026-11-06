import hmac
import json
import re
from asyncio import to_thread
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from models import ChatSearchResult, ChatSession, ChatSessionCreated
from service.subadvise_api_client import proxy_get, proxy_patch, proxy_post, proxy_put


router = APIRouter()


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "UP"}


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    session_id: UUID | None = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank.")
        return value


class AssistantChatResponse(BaseModel):
    session_id: UUID
    response: str


class CreateChatSessionRequest(BaseModel):
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ChatHistorySearchResponse(BaseModel):
    results: list[ChatSearchResult]


class ClearChatDataResponse(BaseModel):
    session_id: UUID
    messages_deleted: int
    context_items_deleted: int


class GroqApiKeyRequest(BaseModel):
    api_key: SecretStr = Field(min_length=1, max_length=512)


class GroqApiKeyUpdatedResponse(BaseModel):
    message: str


class SubscriptionPatchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    subscription_name: str | None = Field(default=None, alias="subscriptionName")
    subscription_date: date | None = Field(default=None, alias="subscriptionDate")
    renewal_date: date | None = Field(default=None, alias="renewalDate")
    subscription_price: Decimal | None = Field(
        default=None,
        alias="subscriptionPrice",
        ge=0,
    )
    currency: str | None = None

    @field_validator("subscription_name")
    @classmethod
    def subscription_name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("subscriptionName must not be blank.")
        return value

    @field_validator("currency")
    @classmethod
    def currency_must_be_iso_code(cls, value: str | None) -> str | None:
        if value is not None and re.fullmatch(r"[A-Z]{3}", value) is None:
            raise ValueError("currency must be a three-letter uppercase currency code.")
        return value

    @model_validator(mode="after")
    def require_a_change(self) -> "SubscriptionPatchRequest":
        if not self.model_fields_set or all(
            getattr(self, field_name) is None for field_name in self.model_fields_set
        ):
            raise ValueError("At least one non-null subscription field is required.")
        return self


class ExpenseTargetRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    target_expense: Decimal = Field(alias="targetExpense", ge=0)
    currency: str
    start_date: date | None = Field(default=None, alias="startDate")
    end_date: date = Field(alias="endDate")

    @field_validator("currency")
    @classmethod
    def currency_must_be_iso_code(cls, value: str) -> str:
        return _parse_tool_currency(value)


class ActualExpenseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    actual_expense: Decimal = Field(alias="actualExpense", ge=0)
    currency: str
    target_id: UUID = Field(alias="targetId")

    @field_validator("currency")
    @classmethod
    def currency_must_be_iso_code(cls, value: str) -> str:
        return _parse_tool_currency(value)


class ExpenseColorThresholdsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    red: Decimal = Field(ge=0, le=100)
    orange: Decimal = Field(ge=0, le=100)
    yellow: Decimal = Field(ge=0, le=100)
    lime: Decimal = Field(ge=0, le=100)
    green: Decimal = Field(ge=0, le=100)

    @model_validator(mode="after")
    def thresholds_must_descend(self) -> "ExpenseColorThresholdsRequest":
        values = (self.red, self.orange, self.yellow, self.lime, self.green)
        if any(higher <= lower for higher, lower in zip(values, values[1:])):
            raise ValueError("Thresholds must strictly descend from red to green.")
        return self


def _require_current_groq_key(
    request: Request,
    authorization: str | None,
) -> None:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="A valid bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supplied_key = authorization.removeprefix("Bearer ")
    if not supplied_key or not hmac.compare_digest(
        supplied_key,
        request.app.state.groq_api_key,
    ):
        raise HTTPException(
            status_code=401,
            detail="A valid bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/api/assistant/chat",
    response_model=AssistantChatResponse,
    summary="Ask the SubAdvise assistant",
    tags=["Assistant"],
)
async def chat_with_assistant(
    body: AssistantChatRequest,
    request: Request,
) -> AssistantChatResponse:
    from service.assistant import AssistantError, answer_question

    try:
        if body.session_id is None:
            session = await to_thread(request.app.state.chat_memory.create_session)
        else:
            session = await to_thread(
                request.app.state.chat_memory.get_session,
                body.session_id,
            )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat session not found.") from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Chat history storage is unavailable.",
        ) from exc

    try:
        response = await answer_question(
            request.app.state.groq_api_key,
            request,
            body.message,
            session.session_id,
        )
    except AssistantError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc
    return AssistantChatResponse(session_id=session.session_id, response=response)


@router.post(
    "/api/assistant/sessions",
    response_model=ChatSessionCreated,
    status_code=201,
    summary="Create an assistant chat session",
    tags=["Assistant"],
)
async def create_chat_session(
    body: CreateChatSessionRequest,
    request: Request,
) -> ChatSessionCreated:
    try:
        session = await to_thread(
            request.app.state.chat_memory.create_session,
            body.metadata,
        )
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Chat history storage is unavailable.",
        ) from exc
    return ChatSessionCreated(
        session_id=session.session_id,
        created_at=session.created_at,
    )


@router.get(
    "/api/assistant/sessions/{session_id}",
    response_model=ChatSession,
    summary="Get a chat session and its full history",
    tags=["Assistant"],
)
async def get_chat_session(
    session_id: UUID,
    request: Request,
) -> ChatSession:
    try:
        return await to_thread(request.app.state.chat_memory.get_session, session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat session not found.") from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Chat history storage is unavailable.",
        ) from exc


@router.delete(
    "/api/assistant/sessions/{session_id}",
    status_code=204,
    summary="Delete a chat session and its history",
    tags=["Assistant"],
)
async def delete_chat_session(
    session_id: UUID,
    request: Request,
) -> Response:
    pending_changes = request.app.state.pending_changes
    async with request.app.state.pending_changes_lock:
        pending_change = pending_changes.get(session_id)
        if pending_change and pending_change["status"] == "confirming":
            raise HTTPException(
                status_code=409,
                detail="A confirmed change is still processing.",
            )
        try:
            await to_thread(request.app.state.chat_memory.delete_session, session_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Chat session not found.") from exc
        except (OSError, RuntimeError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Chat history storage is unavailable.",
            ) from exc
        pending_changes.pop(session_id, None)
    return Response(status_code=204)


@router.delete(
    "/api/assistant/sessions/{session_id}/history",
    response_model=ClearChatDataResponse,
    summary="Clear a session's chat history",
    tags=["Assistant"],
)
async def clear_chat_history(
    session_id: UUID,
    request: Request,
) -> ClearChatDataResponse:
    try:
        deleted_messages = await to_thread(
            request.app.state.chat_memory.clear_chat_history,
            session_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat session not found.") from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Chat history storage is unavailable.",
        ) from exc
    return ClearChatDataResponse(
        session_id=session_id,
        messages_deleted=deleted_messages,
        context_items_deleted=0,
    )


@router.delete(
    "/api/assistant/sessions/{session_id}/context",
    response_model=ClearChatDataResponse,
    summary="Clear a session's semantic context",
    tags=["Assistant"],
)
async def clear_chat_context(
    session_id: UUID,
    request: Request,
) -> ClearChatDataResponse:
    try:
        deleted_context_items = await to_thread(
            request.app.state.chat_memory.clear_context,
            session_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat session not found.") from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Chat memory storage is unavailable.",
        ) from exc
    return ClearChatDataResponse(
        session_id=session_id,
        messages_deleted=0,
        context_items_deleted=deleted_context_items,
    )


@router.delete(
    "/api/assistant/sessions/{session_id}/memory",
    response_model=ClearChatDataResponse,
    summary="Clear a session's chat history and semantic context",
    tags=["Assistant"],
)
async def clear_chat_memory(
    session_id: UUID,
    request: Request,
) -> ClearChatDataResponse:
    try:
        deleted_messages, deleted_context_items = await to_thread(
            request.app.state.chat_memory.clear_all,
            session_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Chat session not found.") from exc
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Chat memory storage is unavailable.",
        ) from exc
    return ClearChatDataResponse(
        session_id=session_id,
        messages_deleted=deleted_messages,
        context_items_deleted=deleted_context_items,
    )


@router.get(
    "/api/assistant/history/search",
    response_model=ChatHistorySearchResponse,
    summary="Search chat history semantically",
    tags=["Assistant"],
)
async def search_chat_history(
    request: Request,
    query: str = Query(min_length=1, max_length=4000),
    session_id: UUID | None = None,
    top_k: int = Query(default=5, ge=1, le=50),
) -> ChatHistorySearchResponse:
    query = query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="query must not be blank.")
    try:
        results = await to_thread(
            request.app.state.chat_memory.search_history,
            query,
            session_id,
            top_k,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Chat vector search is unavailable.",
        ) from exc
    return ChatHistorySearchResponse(results=results)


@router.put(
    "/api/settings/groq-api-key",
    response_model=GroqApiKeyUpdatedResponse,
    summary="Update the Groq API key",
    tags=["Configuration"],
)
async def update_groq_api_key(
    body: GroqApiKeyRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> GroqApiKeyUpdatedResponse:
    async with request.app.state.groq_api_key_lock:
        _require_current_groq_key(request, authorization)
        new_key = body.api_key.get_secret_value().strip()
        if not new_key:
            raise HTTPException(
                status_code=422,
                detail="The Groq API key must not be empty.",
            )
        request.app.state.groq_api_key = new_key

    return GroqApiKeyUpdatedResponse(message="Groq API key updated.")


@router.get(
    "/api/subscriptions",
    summary="Get all subscriptions",
    tags=["Subscriptions"],
)
async def get_subscriptions(request: Request) -> Response:
    return await proxy_get(request, "/api/subscriptions")


@router.get(
    "/api/subscriptions/search",
    summary="Search subscriptions by name",
    tags=["Subscriptions"],
)
async def search_subscriptions_by_name(
    request: Request,
    name: str = Query(min_length=1),
) -> Response:
    name = name.strip()
    if not name:
        raise HTTPException(
            status_code=422,
            detail="name must not be blank.",
        )
    return await proxy_get(
        request,
        "/api/subscriptions/search",
        {"name": name},
    )


@router.get(
    "/api/subscriptions/filter/subscription-date",
    summary="Filter subscriptions by subscription date",
    tags=["Subscriptions"],
)
async def get_subscriptions_by_subscription_date(
    request: Request,
    date: date,
) -> Response:
    return await proxy_get(
        request,
        "/api/subscriptions/filter/subscription-date",
        {"date": date.isoformat()},
    )


@router.get(
    "/api/subscriptions/filter/renewal-date",
    summary="Filter subscriptions by renewal date",
    tags=["Subscriptions"],
)
async def get_subscriptions_by_renewal_date(
    request: Request,
    date: date,
) -> Response:
    return await proxy_get(
        request,
        "/api/subscriptions/filter/renewal-date",
        {"date": date.isoformat()},
    )


@router.get(
    "/api/subscriptions/filter/renewal-range",
    summary="Filter subscriptions by renewal date range",
    tags=["Subscriptions"],
)
async def get_subscriptions_by_renewal_range(
    request: Request,
    start_date: date = Query(alias="startDate"),
    end_date: date = Query(alias="endDate"),
) -> Response:
    return await proxy_get(
        request,
        "/api/subscriptions/filter/renewal-range",
        {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        },
    )


@router.get(
    "/api/subscriptions/filter/subscription-range",
    summary="Filter subscriptions by subscription date range",
    tags=["Subscriptions"],
)
async def get_subscriptions_by_subscription_range(
    request: Request,
    start_date: date = Query(alias="startDate"),
    end_date: date = Query(alias="endDate"),
) -> Response:
    return await proxy_get(
        request,
        "/api/subscriptions/filter/subscription-range",
        {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        },
    )


@router.get(
    "/api/subscriptions/{subscription_id}",
    summary="Get a subscription by ID",
    tags=["Subscriptions"],
)
async def get_subscription_by_id(
    request: Request,
    subscription_id: UUID,
) -> Response:
    return await proxy_get(
        request,
        f"/api/subscriptions/{subscription_id}",
    )


@router.patch(
    "/api/subscriptions/{subscription_id}",
    summary="Partially update a subscription",
    tags=["Subscriptions"],
)
async def patch_subscription(
    request: Request,
    subscription_id: UUID,
    body: SubscriptionPatchRequest,
) -> Response:
    changes = body.model_dump(
        mode="json",
        by_alias=True,
        exclude_unset=True,
        exclude_none=True,
    )
    if "subscriptionPrice" in changes:
        changes["subscriptionPrice"] = float(changes["subscriptionPrice"])
    return await proxy_patch(
        request,
        f"/api/subscriptions/{subscription_id}",
        changes,
    )


@router.get(
    "/api/currency/convert",
    summary="Convert an amount between currencies",
    tags=["Currency"],
)
async def convert_currency(
    request: Request,
    amount: Decimal = Query(ge=0),
    from_currency: str = Query(alias="from"),
    to_currency: str = Query(alias="to"),
) -> Response:
    return await proxy_get(
        request,
        "/api/currency/convert",
        {
            "amount": str(amount),
            "from": from_currency,
            "to": to_currency,
        },
    )


@router.get(
    "/api/expenses/monthly",
    summary="Get monthly expenses",
    tags=["Expenses"],
)
async def get_monthly_expenses(
    request: Request,
    year: int,
    month: int = Query(ge=1, le=12),
) -> Response:
    return await proxy_get(
        request,
        "/api/expenses/monthly",
        {"year": year, "month": month},
    )


@router.post(
    "/api/expenses/targets",
    status_code=201,
    summary="Create an expense target",
    tags=["Expenses"],
)
async def create_expense_target(
    request: Request,
    body: ExpenseTargetRequest,
) -> Response:
    payload = body.model_dump(mode="json", by_alias=True, exclude_none=True)
    payload["targetExpense"] = float(body.target_expense)
    return await proxy_post(request, "/api/expenses/targets", payload)


@router.post(
    "/api/expenses",
    status_code=201,
    summary="Record an actual expense",
    tags=["Expenses"],
)
async def create_actual_expense(
    request: Request,
    body: ActualExpenseRequest,
) -> Response:
    payload = body.model_dump(mode="json", by_alias=True)
    payload["actualExpense"] = float(body.actual_expense)
    return await proxy_post(request, "/api/expenses", payload)


@router.get(
    "/api/expenses/color-thresholds",
    summary="Get expense color thresholds",
    tags=["Expenses"],
)
async def get_expense_color_thresholds(request: Request) -> Response:
    return await proxy_get(request, "/api/expenses/color-thresholds")


@router.put(
    "/api/expenses/color-thresholds",
    summary="Update expense color thresholds",
    tags=["Expenses"],
)
async def put_expense_color_thresholds(
    request: Request,
    body: ExpenseColorThresholdsRequest,
) -> Response:
    payload = {
        color: float(getattr(body, color))
        for color in ("red", "orange", "yellow", "lime", "green")
    }
    return await proxy_put(request, "/api/expenses/color-thresholds", payload)


async def invoke_assistant_tool(
    request: Request,
    name: str,
    raw_arguments: str,
    session_id: UUID,
) -> str:
    try:
        arguments: Any = json.loads(raw_arguments)
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object.")

        if name == "get_all_subscriptions":
            _require_arguments(arguments, set())
            response = await get_subscriptions(request)
        elif name == "search_subscriptions_by_name":
            _require_arguments(arguments, {"name"})
            subscription_name = arguments["name"]
            if not isinstance(subscription_name, str) or not subscription_name.strip():
                raise ValueError("The name must not be blank.")
            response = await search_subscriptions_by_name(
                request,
                subscription_name,
            )
        elif name == "get_subscription_by_id":
            _require_arguments(arguments, {"subscription_id"})
            response = await get_subscription_by_id(
                request,
                UUID(arguments["subscription_id"]),
            )
        elif name == "get_subscriptions_by_subscription_date":
            _require_arguments(arguments, {"date"})
            response = await get_subscriptions_by_subscription_date(
                request,
                _parse_tool_date(arguments["date"]),
            )
        elif name == "get_subscriptions_by_renewal_date":
            _require_arguments(arguments, {"date"})
            response = await get_subscriptions_by_renewal_date(
                request,
                _parse_tool_date(arguments["date"]),
            )
        elif name == "get_subscriptions_by_renewal_range":
            _require_arguments(arguments, {"startDate", "endDate"})
            response = await get_subscriptions_by_renewal_range(
                request,
                _parse_tool_date(arguments["startDate"]),
                _parse_tool_date(arguments["endDate"]),
            )
        elif name == "get_subscriptions_by_subscription_range":
            _require_arguments(arguments, {"startDate", "endDate"})
            response = await get_subscriptions_by_subscription_range(
                request,
                _parse_tool_date(arguments["startDate"]),
                _parse_tool_date(arguments["endDate"]),
            )
        elif name == "convert_currency":
            _require_arguments(arguments, {"amount", "from", "to"})
            amount = Decimal(str(arguments["amount"]))
            if not amount.is_finite() or amount < 0:
                raise ValueError("The amount must be a non-negative number.")
            from_currency = _parse_tool_currency(arguments["from"])
            to_currency = _parse_tool_currency(arguments["to"])
            response = await convert_currency(
                request,
                amount,
                from_currency,
                to_currency,
            )
        elif name == "get_monthly_expenses":
            _require_arguments(arguments, {"year", "month"})
            year = arguments["year"]
            month = arguments["month"]
            if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
                raise ValueError("The year must be between 1 and 9999.")
            if isinstance(month, bool) or not isinstance(month, int) or not 1 <= month <= 12:
                raise ValueError("The month must be between 1 and 12.")
            response = await get_monthly_expenses(request, year, month)
        elif name == "get_expense_color_thresholds":
            _require_arguments(arguments, set())
            response = await get_expense_color_thresholds(request)
        elif name == "stage_subscription_update":
            expected = {
                "subscription_id",
                "subscriptionName",
                "subscriptionDate",
                "renewalDate",
                "subscriptionPrice",
                "currency",
            }
            _require_arguments(arguments, expected)
            subscription_id = UUID(arguments["subscription_id"])
            patch = SubscriptionPatchRequest.model_validate(
                {
                    key: value
                    for key, value in arguments.items()
                    if key != "subscription_id" and value is not None
                }
            )
            changes = patch.model_dump(
                mode="json",
                by_alias=True,
                exclude_unset=True,
                exclude_none=True,
            )
            pending = request.app.state.pending_changes
            async with request.app.state.pending_changes_lock:
                if session_id in pending:
                    return json.dumps(
                        {
                            "error": (
                                "A subscription update is already awaiting "
                                "confirmation in this chat."
                            )
                        }
                    )
            current_response = await get_subscription_by_id(request, subscription_id)
            if not 200 <= current_response.status_code < 300:
                return json.dumps(
                    {
                        "status_code": current_response.status_code,
                        "error": current_response.body.decode(
                            "utf-8",
                            errors="replace",
                        ),
                    }
                )
            try:
                current_subscription = json.loads(current_response.body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                current_subscription = current_response.body.decode(
                    "utf-8",
                    errors="replace",
                )
            async with request.app.state.pending_changes_lock:
                if session_id in pending:
                    return json.dumps(
                        {
                            "error": (
                                "A subscription update is already awaiting "
                                "confirmation in this chat."
                            )
                        }
                    )
                pending[session_id] = {
                    "kind": "subscription_update",
                    "subscription_id": str(subscription_id),
                    "changes": changes,
                    "current": current_subscription,
                    "status": "awaiting_confirmation",
                }
            return json.dumps(
                {
                    "status": "awaiting_confirmation",
                    "current_subscription": current_subscription,
                    "proposed_changes": changes,
                },
                ensure_ascii=True,
                default=str,
            )
        elif name == "stage_expense_target":
            _require_arguments(
                arguments,
                {"targetExpense", "currency", "startDate", "endDate"},
            )
            target = ExpenseTargetRequest.model_validate(
                {
                    key: value
                    for key, value in arguments.items()
                    if value is not None
                }
            )
            payload = target.model_dump(
                mode="json",
                by_alias=True,
                exclude_none=True,
            )
            payload["targetExpense"] = float(target.target_expense)
            return await _stage_confirmation(
                request,
                session_id,
                kind="expense_target",
                changes=payload,
            )
        elif name == "stage_actual_expense":
            _require_arguments(
                arguments,
                {"actualExpense", "currency", "targetId"},
            )
            expense = ActualExpenseRequest.model_validate(arguments)
            payload = expense.model_dump(mode="json", by_alias=True)
            payload["actualExpense"] = float(expense.actual_expense)
            return await _stage_confirmation(
                request,
                session_id,
                kind="actual_expense",
                changes=payload,
            )
        elif name == "stage_expense_color_thresholds":
            expected = {"red", "orange", "yellow", "lime", "green"}
            _require_arguments(arguments, expected)
            thresholds = ExpenseColorThresholdsRequest.model_validate(arguments)
            payload = {
                color: float(getattr(thresholds, color))
                for color in ("red", "orange", "yellow", "lime", "green")
            }
            return await _stage_confirmation(
                request,
                session_id,
                kind="expense_color_thresholds",
                changes=payload,
            )
        else:
            raise ValueError("Unknown SubAdvise API operation.")
    except HTTPException as exc:
        return json.dumps({"status_code": exc.status_code, "error": exc.detail})
    except (InvalidOperation, KeyError, TypeError, ValueError) as exc:
        return json.dumps({"error": str(exc)})

    try:
        data: Any = json.loads(response.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        data = response.body.decode("utf-8", errors="replace")
    return json.dumps(
        {"status_code": response.status_code, "data": data},
        ensure_ascii=True,
        default=str,
    )


def _require_arguments(
    arguments: dict[str, Any],
    expected: set[str],
) -> None:
    if arguments.keys() != expected:
        raise ValueError("Tool arguments do not match the endpoint parameters.")


async def _stage_confirmation(
    request: Request,
    session_id: UUID,
    *,
    kind: str,
    changes: dict[str, Any],
) -> str:
    pending = request.app.state.pending_changes
    async with request.app.state.pending_changes_lock:
        if session_id in pending:
            return json.dumps(
                {"error": "A change is already awaiting confirmation in this chat."}
            )
        pending[session_id] = {
            "kind": kind,
            "changes": changes,
            "status": "awaiting_confirmation",
        }
    return json.dumps(
        {
            "status": "awaiting_confirmation",
            "change_type": kind,
            "proposed_changes": changes,
        },
        ensure_ascii=True,
    )


async def resolve_pending_change(
    request: Request,
    session_id: UUID,
    *,
    approve: bool,
) -> str | None:
    pending = request.app.state.pending_changes
    lock = request.app.state.pending_changes_lock
    async with lock:
        update = pending.get(session_id)
        if update is None:
            return None
        if update["status"] == "confirming":
            return "The confirmed change is already being processed."
        if not approve:
            del pending[session_id]
            return "The change was cancelled; no changes were made."
        update["status"] = "confirming"

    try:
        if update["kind"] == "subscription_update":
            response = await patch_subscription(
                request,
                UUID(update["subscription_id"]),
                SubscriptionPatchRequest.model_validate(update["changes"]),
            )
        elif update["kind"] == "expense_target":
            response = await create_expense_target(
                request,
                ExpenseTargetRequest.model_validate(update["changes"]),
            )
        elif update["kind"] == "actual_expense":
            response = await create_actual_expense(
                request,
                ActualExpenseRequest.model_validate(update["changes"]),
            )
        elif update["kind"] == "expense_color_thresholds":
            response = await put_expense_color_thresholds(
                request,
                ExpenseColorThresholdsRequest.model_validate(update["changes"]),
            )
        else:
            async with lock:
                if pending.get(session_id) is update:
                    update["status"] = "awaiting_confirmation"
            return "That change could not be completed."
    except HTTPException as exc:
        async with lock:
            if pending.get(session_id) is update:
                update["status"] = "awaiting_confirmation"
        return "The change could not be completed. It remains pending for confirmation."

    async with lock:
        if 200 <= response.status_code < 300:
            pending.pop(session_id, None)
            return "The requested change was completed successfully."
        if pending.get(session_id) is update:
            update["status"] = "awaiting_confirmation"
    return "The change could not be completed. It remains pending for confirmation."


def _parse_tool_date(value: Any) -> date:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError("Date arguments must use YYYY-MM-DD format.")
    return date.fromisoformat(value)


def _parse_tool_currency(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Z]{3}", value) is None:
        raise ValueError("Currency codes must be three uppercase letters.")
    return value
