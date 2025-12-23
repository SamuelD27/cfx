<template>
  <AppLayout>
    <div class="space-y-6">
      <div>
        <h1 class="text-3xl font-bold tracking-tight">Settings</h1>
        <p class="text-muted-foreground">
          Configure your CharForge environment and model settings
        </p>
      </div>

      <!-- Environment Settings -->
      <Card class="p-6">
        <h2 class="text-xl font-semibold mb-4">Environment Settings</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-1">Hugging Face Token</label>
            <Input
              v-model="envSettings.HF_TOKEN"
              type="password"
              placeholder="Enter your Hugging Face token"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium mb-1">Hugging Face Home</label>
            <Input
              v-model="envSettings.HF_HOME"
              placeholder="Enter HF home directory path"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium mb-1">CivitAI API Key</label>
            <Input
              v-model="envSettings.CIVITAI_API_KEY"
              type="password"
              placeholder="Enter your CivitAI API key"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium mb-1">Google API Key</label>
            <Input
              v-model="envSettings.GOOGLE_API_KEY"
              type="password"
              placeholder="Enter your Google API key"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium mb-1">Fal API Key</label>
            <Input
              v-model="envSettings.FAL_KEY"
              type="password"
              placeholder="Enter your Fal API key"
            />
          </div>
          
          <!-- Model URL Settings -->
          <div class="mt-6 pt-6 border-t">
            <h3 class="text-lg font-medium mb-4">Model URLs</h3>
            
            <div class="space-y-4">
              <div>
                <label class="block text-sm font-medium mb-1">Training Model URL</label>
                <Input
                  v-model="envSettings.TRAINING_MODEL_URL"
                  placeholder="https://huggingface.co/black-forest-labs/FLUX.1-Krea-dev"
                />
                <p class="text-xs text-muted-foreground mt-1">
                  Default: black-forest-labs/FLUX.1-Krea-dev
                </p>
              </div>
              
              <div>
                <label class="block text-sm font-medium mb-1">MV Adapter URL</label>
                <Input
                  v-model="envSettings.MV_ADAPTER_URL"
                  placeholder="https://github.com/MV-Adapter/model"
                />
                <p class="text-xs text-muted-foreground mt-1">
                  Default: mv-adapter/model
                </p>
              </div>
              
              <div>
                <label class="block text-sm font-medium mb-1">ComfyUI URL</label>
                <Input
                  v-model="envSettings.COMFYUI_URL"
                  placeholder="https://github.com/comfyanonymous/ComfyUI"
                />
                <p class="text-xs text-muted-foreground mt-1">
                  Default: comfyui/models
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <div class="mt-6 flex justify-end">
          <Button @click="saveEnvironmentSettings" :disabled="isSaving">
            <Save class="mr-2 h-4 w-4" />
            {{ isSaving ? 'Saving...' : 'Save Settings' }}
          </Button>
        </div>
      </Card>
      
      <!-- Environment Validation -->
      <Card class="p-6">
        <h2 class="text-xl font-semibold mb-4">Environment Validation</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="(result, key) in validationResults" :key="key" class="p-4 rounded-lg" 
               :class="result.valid ? 'bg-green-50' : 'bg-red-50'">
            <div class="flex items-center">
              <CheckCircle2 v-if="result.valid" class="mr-2 h-5 w-5 text-green-500" />
              <XCircle v-else class="mr-2 h-5 w-5 text-red-500" />
              <span class="font-medium">{{ String(key).replace('_', ' ') }}</span>
            </div>
            <p class="mt-1 text-sm" :class="result.valid ? 'text-green-700' : 'text-red-700'">
              {{ result.message }}
            </p>
          </div>
        </div>
        
        <div class="mt-6">
          <Button @click="validateEnvironment" :disabled="isValidating">
            <RefreshCw :class="{ 'animate-spin': isValidating }" class="mr-2 h-4 w-4" />
            {{ isValidating ? 'Validating...' : 'Validate Environment' }}
          </Button>
        </div>
      </Card>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import { 
  Save, CheckCircle2, XCircle, RefreshCw 
} from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Button from '@/components/ui/Button.vue'
import { settingsApi } from '@/services/api'

// Environment settings
const envSettings = ref({
  HF_TOKEN: '',
  HF_HOME: '',
  CIVITAI_API_KEY: '',
  GOOGLE_API_KEY: '',
  FAL_KEY: '',
  TRAINING_MODEL_URL: '',
  MV_ADAPTER_URL: '',
  MV_ADAPTER_LORA_URLS: '',
  COMFYUI_URL: '',
  CAPTIONING_SYSTEM_PROMPT: '',
  GENERATION_SYSTEM_PROMPT: ''
})

const validationResults = ref<Record<string, { valid: boolean; message: string }>>({})
const isSaving = ref(false)
const isValidating = ref(false)
const toast = useToast()

// Load environment settings
const loadEnvironmentSettings = async () => {
  try {
    const settings = await settingsApi.getEnvironment()
    envSettings.value = { ...settings }
  } catch (error) {
    toast.error('Failed to load environment settings')
  }
}

// Save environment settings
const saveEnvironmentSettings = async () => {
  isSaving.value = true
  try {
    await settingsApi.saveEnvironment(envSettings.value)
    toast.success('Environment settings saved successfully')
    validateEnvironment() // Re-validate after saving
  } catch (error) {
    toast.error('Failed to save environment settings')
  } finally {
    isSaving.value = false
  }
}

// Validate environment settings
const validateEnvironment = async () => {
  isValidating.value = true
  try {
    const results = await settingsApi.testEnvironment()
    validationResults.value = results
  } catch (error) {
    toast.error('Failed to validate environment settings')
  } finally {
    isValidating.value = false
  }
}

onMounted(() => {
  loadEnvironmentSettings()
  validateEnvironment()
})
</script>