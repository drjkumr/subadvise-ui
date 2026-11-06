from collections.abc import Mapping

import httpx
from fastapi import HTTPException, Request, Response


async def proxy_get(
    request: Request,
    path: str,
    params: Mapping[str, str | int] | None = None,
) -> Response:
    client: httpx.AsyncClient = request.app.state.subadvise_client

    try:
        upstream_response = await fetch_get(client, path, params)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The SubAdvise API request timed out.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="The SubAdvise API is unavailable.",
        ) from exc

    headers = {}
    content_type = upstream_response.headers.get("content-type")
    if content_type is not None:
        headers["content-type"] = content_type

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=headers,
    )


async def proxy_patch(
    request: Request,
    path: str,
    json: Mapping[str, object],
) -> Response:
    client: httpx.AsyncClient = request.app.state.subadvise_client

    try:
        upstream_response = await client.patch(path, json=json)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The SubAdvise API update request timed out.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="The SubAdvise API is unavailable.",
        ) from exc

    headers = {}
    content_type = upstream_response.headers.get("content-type")
    if content_type is not None:
        headers["content-type"] = content_type

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=headers,
    )


async def proxy_post(
    request: Request,
    path: str,
    json: Mapping[str, object],
) -> Response:
    client: httpx.AsyncClient = request.app.state.subadvise_client

    try:
        upstream_response = await client.post(path, json=json)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The SubAdvise API request timed out.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="The SubAdvise API is unavailable.",
        ) from exc

    return _response_from_upstream(upstream_response)


async def proxy_put(
    request: Request,
    path: str,
    json: Mapping[str, object],
) -> Response:
    client: httpx.AsyncClient = request.app.state.subadvise_client

    try:
        upstream_response = await client.put(path, json=json)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="The SubAdvise API request timed out.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="The SubAdvise API is unavailable.",
        ) from exc

    return _response_from_upstream(upstream_response)


def _response_from_upstream(upstream_response: httpx.Response) -> Response:
    headers = {}
    content_type = upstream_response.headers.get("content-type")
    if content_type is not None:
        headers["content-type"] = content_type
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=headers,
    )


async def fetch_get(
    client: httpx.AsyncClient,
    path: str,
    params: Mapping[str, str | int] | None = None,
) -> httpx.Response:
    return await client.get(path, params=params)
