<template>
  <AppLayout>
    <div class="space-y-6">
      <div>
        <h1 class="text-3xl font-bold tracking-tight">Training Sessions</h1>
        <p class="text-muted-foreground">
          Monitor your character training progress and history
        </p>
      </div>

      <!-- Active Training Sessions -->
      <div v-if="activeSessions.length > 0">
        <h2 class="text-xl font-semibold mb-4">Active Training</h2>
        <div class="space-y-4">
          <Card
            v-for="session in activeSessions"
            :key="session.id"
            class="p-6"
          >
            <div class="space-y-4">
              <!-- Session Header -->
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-lg font-semibold">{{ session.character_name }}</h3>
                  <p class="text-sm text-muted-foreground">
                    Started {{ formatDate(session.started_at) }}
                  </p>
                </div>
                <StatusBadge :status="session.status" />
              </div>

              <!-- Progress Bar -->
              <div class="space-y-2">
                <div class="flex justify-between text-sm">
                  <span>Training Progress</span>
                  <span>{{ Math.round(session.progress) }}%</span>
                </div>
                <div class="w-full bg-muted rounded-full h-2">
                  <div
                    class="bg-primary h-2 rounded-full transition-all duration-500"
                    :style="{ width: `${session.progress}%` }"
                  ></div>
                </div>
              </div>

              <!-- Training Details -->
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p class="text-muted-foreground">Steps</p>
                  <p class="font-medium">{{ session.steps || 'N/A' }}</p>
                </div>
                <div>
                  <p class="text-muted-foreground">Learning Rate</p>
                  <p class="font-medium">{{ session.learning_rate || 'N/A' }}</p>
                </div>
                <div>
                  <p class="text-muted-foreground">Batch Size</p>
                  <p class="font-medium">{{ session.batch_size || 'N/A' }}</p>
                </div>
                <div>
                  <p class="text-muted-foreground">Rank</p>
                  <p class="font-medium">{{ session.rank_dim || 'N/A' }}</p>
                </div>
              </div>

              <!-- Actions -->
              <div class="flex justify-end space-x-2">
                <Button
                  @click="viewLogs(session)"
                  variant="outline"
                  size="sm"
                >
                  <FileText class="mr-2 h-3 w-3" />
                  View Logs
                </Button>
                <Button
                  v-if="session.status === 'completed'"
                  @click="$router.push(`/inference?character=${session.character_id}`)"
                  size="sm"
                >
                  <Wand2 class="mr-2 h-3 w-3" />
                  Generate Images
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <!-- Training History -->
      <div>
        <h2 class="text-xl font-semibold mb-4">Training History</h2>

        <div v-if="historySessions.length > 0" class="space-y-3">
          <Card
            v-for="session in historySessions"
            :key="session.id"
            class="p-4 hover:bg-accent transition-colors cursor-pointer"
            @click="selectedSession = session"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-4">
                <div>
                  <h4 class="font-medium">{{ session.character_name }}</h4>
                  <p class="text-sm text-muted-foreground">
                    {{ formatDate(session.created_at) }}
                    {{ session.completed_at ? `• Completed in ${getTrainingDuration(session)}` : '' }}
                  </p>
                </div>
              </div>

              <div class="flex items-center space-x-3">
                <div class="text-right text-sm">
                  <p class="font-medium">{{ session.steps }} steps</p>
                  <p class="text-muted-foreground">{{ Math.round(session.progress) }}%</p>
                </div>
                <StatusBadge :status="session.status" />
              </div>
            </div>
          </Card>
        </div>

        <div v-else-if="!isLoading" class="text-center py-8">
          <div class="mx-auto w-12 h-12 bg-muted rounded-lg flex items-center justify-center mb-3">
            <Zap class="h-6 w-6 text-muted-foreground" />
          </div>
          <p class="text-muted-foreground">No training sessions yet</p>
          <Button @click="$router.push('/characters/create')" class="mt-3">
            Create Character
          </Button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
        <p class="text-muted-foreground">Loading training sessions...</p>
      </div>
    </div>

    <!-- Session Detail Modal -->
    <div
      v-if="selectedSession"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      @click="selectedSession = null"
    >
      <div
        class="bg-background rounded-lg max-w-2xl w-full max-h-[80vh] overflow-auto"
        @click.stop
      >
        <div class="p-6">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-lg font-semibold">{{ selectedSession.character_name }}</h3>
              <p class="text-sm text-muted-foreground">
                Training Session #{{ selectedSession.id }}
              </p>
            </div>
            <Button @click="selectedSession = null" variant="ghost" size="sm">
              <X class="h-4 w-4" />
            </Button>
          </div>

          <div class="space-y-4">
            <!-- Status and Progress -->
            <div class="flex items-center justify-between p-4 bg-muted rounded-lg">
              <div>
                <StatusBadge :status="selectedSession.status" />
                <p class="text-sm text-muted-foreground mt-1">
                  {{ Math.round(selectedSession.progress) }}% complete
                </p>
              </div>
              <div class="text-right text-sm">
                <p>Started: {{ formatDate(selectedSession.started_at) }}</p>
                <p v-if="selectedSession.completed_at">
                  Completed: {{ formatDate(selectedSession.completed_at) }}
                </p>
              </div>
            </div>

            <!-- Training Configuration -->
            <div>
              <h4 class="font-medium mb-2">Configuration</h4>
              <div class="grid grid-cols-2 gap-3 text-sm">
                <div class="flex justify-between">
                  <span class="text-muted-foreground">Steps:</span>
                  <span>{{ selectedSession.steps }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-muted-foreground">Learning Rate:</span>
                  <span>{{ selectedSession.learning_rate }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-muted-foreground">Batch Size:</span>
                  <span>{{ selectedSession.batch_size }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-muted-foreground">Rank:</span>
                  <span>{{ selectedSession.rank_dim }}</span>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex justify-end space-x-2 pt-4 border-t">
              <Button @click="viewLogs(selectedSession)" variant="outline">
                <FileText class="mr-2 h-4 w-4" />
                View Logs
              </Button>
              <Button
                v-if="selectedSession.status === 'completed'"
                @click="$router.push(`/inference?character=${selectedSession.character_id}`)"
              >
                <Wand2 class="mr-2 h-4 w-4" />
                Generate Images
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Logs Modal -->
    <div
      v-if="showLogs"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      @click="showLogs = false"
    >
      <div
        class="bg-background rounded-lg max-w-4xl w-full max-h-[80vh] overflow-auto"
        @click.stop
      >
        <div class="p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold">Training Logs</h3>
            <Button @click="showLogs = false" variant="ghost" size="sm">
              <X class="h-4 w-4" />
            </Button>
          </div>

          <div class="bg-black text-green-400 p-4 rounded-lg font-mono text-sm max-h-96 overflow-auto">
            <pre>{{ logs || 'No logs available yet...' }}</pre>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'vue-toastification'
import { Zap, FileText, Wand2, X } from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { trainingApi, charactersApi, type TrainingSession } from '@/services/api'

const route = useRoute()
const toast = useToast()

const sessions = ref<TrainingSession[]>([])
const selectedSession = ref<TrainingSession | null>(null)
const showLogs = ref(false)
const logs = ref('')
const isLoading = ref(false)

// Computed properties
const activeSessions = computed(() =>
  sessions.value.filter(s => ['pending', 'running'].includes(s.status))
)

const historySessions = computed(() =>
  sessions.value.filter(s => ['completed', 'failed'].includes(s.status))
)

const loadTrainingSessions = async () => {
  isLoading.value = true
  try {
    // Get all characters first
    const characters = await charactersApi.list()

    // For each character, get its training sessions
    const allSessions: TrainingSession[] = []
    for (const character of characters) {
      try {
        const charSessions = await trainingApi.getTrainingSessions(character.id)
        // Add character name to each session
        for (const session of charSessions) {
          allSessions.push({
            ...session,
            character_name: character.name
          })
        }
      } catch (e) {
        // Skip characters with no training sessions
        console.log(`No training sessions for ${character.name}`)
      }
    }

    // Sort by created_at descending (newest first)
    sessions.value = allSessions.sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  } catch (error: any) {
    toast.error('Failed to load training sessions')
    console.error('Error loading training sessions:', error)
  } finally {
    isLoading.value = false
  }
}

const viewLogs = (session: TrainingSession) => {
  selectedSession.value = session
  logs.value = `Training logs for ${session.character_name}...\n\nThis feature will show real-time training logs.`
  showLogs.value = true
}

const formatDate = (dateString: string | null): string => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}

const getTrainingDuration = (session: TrainingSession): string => {
  if (!session.started_at || !session.completed_at) return 'N/A'

  const start = new Date(session.started_at)
  const end = new Date(session.completed_at)
  const duration = end.getTime() - start.getTime()

  const minutes = Math.floor(duration / 60000)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  } else {
    return `${minutes}m`
  }
}

// WebSocket connection for real-time updates
let ws: WebSocket | null = null

const connectWebSocket = () => {
  // This would connect to a WebSocket endpoint for real-time training updates
  // ws = new WebSocket('ws://localhost:8000/ws/training')
  // ws.onmessage = (event) => {
  //   const data = JSON.parse(event.data)
  //   // Update training progress in real-time
  // }
}

onMounted(() => {
  loadTrainingSessions()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>
