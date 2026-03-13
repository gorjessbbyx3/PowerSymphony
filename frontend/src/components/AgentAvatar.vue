<template>
  <div class="agent-avatar-wrap" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="24" cy="24" r="23" :fill="bgColor" fill-opacity="0.15" :stroke="agentColor" stroke-width="1.5" stroke-opacity="0.3"/>

      <template v-if="icon === 'crown'">
        <circle cx="24" cy="18" r="8" :fill="agentColor" fill-opacity="0.2"/>
        <circle cx="24" cy="18" r="5" :fill="agentColor"/>
        <path d="M14 36c0-5.5 4.5-10 10-10s10 4.5 10 10" :fill="agentColor" fill-opacity="0.3"/>
        <path d="M18 12l3 4h6l3-4" :stroke="agentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/>
        <circle cx="18" cy="11" r="1.5" :fill="agentColor"/>
        <circle cx="30" cy="11" r="1.5" :fill="agentColor"/>
        <circle cx="24" cy="9" r="1.5" :fill="agentColor"/>
      </template>

      <template v-else-if="icon === 'search'">
        <circle cx="24" cy="18" r="8" :fill="agentColor" fill-opacity="0.2"/>
        <circle cx="24" cy="18" r="5" :fill="agentColor"/>
        <path d="M14 36c0-5.5 4.5-10 10-10s10 4.5 10 10" :fill="agentColor" fill-opacity="0.3"/>
        <circle cx="22" cy="16" r="3.5" stroke="white" stroke-width="1.5" fill="none"/>
        <line x1="25" y1="19" x2="28" y2="22" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
      </template>

      <template v-else-if="icon === 'lightbulb'">
        <circle cx="24" cy="18" r="8" :fill="agentColor" fill-opacity="0.2"/>
        <circle cx="24" cy="18" r="5" :fill="agentColor"/>
        <path d="M14 36c0-5.5 4.5-10 10-10s10 4.5 10 10" :fill="agentColor" fill-opacity="0.3"/>
        <path d="M24 11a5 5 0 0 1 3 9v2h-6v-2a5 5 0 0 1 3-9z" fill="white" fill-opacity="0.9"/>
        <line x1="22" y1="23" x2="26" y2="23" stroke="white" stroke-width="1" stroke-linecap="round"/>
      </template>

      <template v-else-if="icon === 'code'">
        <circle cx="24" cy="18" r="8" :fill="agentColor" fill-opacity="0.2"/>
        <circle cx="24" cy="18" r="5" :fill="agentColor"/>
        <path d="M14 36c0-5.5 4.5-10 10-10s10 4.5 10 10" :fill="agentColor" fill-opacity="0.3"/>
        <polyline points="20,15 17,18 20,21" stroke="white" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="28,15 31,18 28,21" stroke="white" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="25" y1="14" x2="23" y2="22" stroke="white" stroke-width="1" stroke-linecap="round"/>
      </template>

      <template v-else-if="icon === 'plug'">
        <circle cx="24" cy="18" r="8" :fill="agentColor" fill-opacity="0.2"/>
        <circle cx="24" cy="18" r="5" :fill="agentColor"/>
        <path d="M14 36c0-5.5 4.5-10 10-10s10 4.5 10 10" :fill="agentColor" fill-opacity="0.3"/>
        <line x1="21" y1="13" x2="21" y2="17" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="27" y1="13" x2="27" y2="17" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M20 17h8v2a4 4 0 0 1-8 0v-2z" stroke="white" stroke-width="1.2" fill="none"/>
        <line x1="24" y1="23" x2="24" y2="25" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
      </template>

      <template v-else-if="icon === 'shield'">
        <circle cx="24" cy="18" r="8" :fill="agentColor" fill-opacity="0.2"/>
        <circle cx="24" cy="18" r="5" :fill="agentColor"/>
        <path d="M14 36c0-5.5 4.5-10 10-10s10 4.5 10 10" :fill="agentColor" fill-opacity="0.3"/>
        <path d="M24 12l6 3v5c0 3.5-2.5 6.5-6 8-3.5-1.5-6-4.5-6-8v-5l6-3z" fill="white" fill-opacity="0.9"/>
        <polyline points="21,18 23.5,20.5 27,16" :stroke="agentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </template>

      <template v-else-if="icon === 'megaphone'">
        <circle cx="24" cy="18" r="8" :fill="agentColor" fill-opacity="0.2"/>
        <circle cx="24" cy="18" r="5" :fill="agentColor"/>
        <path d="M14 36c0-5.5 4.5-10 10-10s10 4.5 10 10" :fill="agentColor" fill-opacity="0.3"/>
        <path d="M28 13l-6 3h-3a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h3l6 3V13z" fill="white" fill-opacity="0.9"/>
        <path d="M29 15.5v5" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M31 14v8" stroke="white" stroke-width="1" stroke-linecap="round" opacity="0.5"/>
      </template>

      <template v-else-if="icon === 'chart'">
        <circle cx="24" cy="18" r="8" :fill="agentColor" fill-opacity="0.2"/>
        <circle cx="24" cy="18" r="5" :fill="agentColor"/>
        <path d="M14 36c0-5.5 4.5-10 10-10s10 4.5 10 10" :fill="agentColor" fill-opacity="0.3"/>
        <line x1="19" y1="22" x2="19" y2="14" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="22.5" y1="22" x2="22.5" y2="17" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="26" y1="22" x2="26" y2="12" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="29.5" y1="22" x2="29.5" y2="15" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
      </template>

      <template v-else>
        <circle cx="24" cy="18" r="8" :fill="agentColor" fill-opacity="0.2"/>
        <circle cx="24" cy="18" r="5" :fill="agentColor"/>
        <path d="M14 36c0-5.5 4.5-10 10-10s10 4.5 10 10" :fill="agentColor" fill-opacity="0.3"/>
        <text x="24" y="20" text-anchor="middle" dominant-baseline="central" fill="white" font-size="8" font-weight="700">{{ letter }}</text>
      </template>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  agentId: { type: String, default: '' },
  color: { type: String, default: '#58a6ff' },
  icon: { type: String, default: '' },
  letter: { type: String, default: '?' },
  size: { type: Number, default: 48 }
})

const agentColor = computed(() => props.color)
const bgColor = computed(() => props.color)
</script>

<style scoped>
.agent-avatar-wrap {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
