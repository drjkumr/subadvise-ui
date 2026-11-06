<script setup>
import { ref } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  subscription: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'confirm'])

const isDeleting = ref(false)

async function handleConfirm() {
  if (!props.subscription) return
  isDeleting.value = true
  try {
    emit('confirm', props.subscription.subscriptionId)
  } finally {
    isDeleting.value = false
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape') {
    emit('close')
  }
}
</script>

<template>
  <div
    v-if="isOpen"
    class="modal-overlay"
    @click.self="emit('close')"
    @keydown="handleKeydown"
    role="dialog"
    aria-modal="true"
    aria-labelledby="delete-dialog-title"
  >
    <div class="modal-dialog" style="max-width: 440px;">
      <header class="modal-header">
        <h3 id="delete-dialog-title" class="modal-title" style="color: #b91c1c;">
          Delete Subscription
        </h3>
        <button
          type="button"
          class="modal-close-btn"
          @click="emit('close')"
          aria-label="Close modal"
        >
          &times;
        </button>
      </header>

      <div class="modal-body">
        <p style="margin: 0; font-size: 0.9rem; line-height: 1.6; color: var(--ink);">
          Are you sure you want to delete
          <strong>{{ subscription?.subscriptionName || 'this subscription' }}</strong>?
        </p>
        <p style="margin: 0.65rem 0 0; font-size: 0.8rem; color: var(--muted);">
          This action will permanently delete this record from the database. It cannot be undone.
        </p>
      </div>

      <footer class="modal-footer">
        <button
          type="button"
          class="btn-modal-cancel"
          @click="emit('close')"
          :disabled="isDeleting"
        >
          Cancel
        </button>
        <button
          type="button"
          class="btn-modal-danger"
          @click="handleConfirm"
          :disabled="isDeleting"
        >
          <span v-if="isDeleting">Deleting...</span>
          <span v-else>Confirm Delete</span>
        </button>
      </footer>
    </div>
  </div>
</template>

