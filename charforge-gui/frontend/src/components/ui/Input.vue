<template>
  <input
    :value="modelValue"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    :class="cn(
      'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
      $attrs.class ?? ''
    )"
    v-bind="filteredAttrs"
  />
</template>

<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { cn } from '@/lib/utils'

defineProps<{
  modelValue?: string | number
}>()

defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const attrs = useAttrs()
const filteredAttrs = computed(() => {
  const { class: _, modelValue: __, 'onUpdate:modelValue': ___, ...rest } = attrs
  return rest
})
</script>
