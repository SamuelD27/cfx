<template>
  <AppLayout>
    <div class="space-y-6">
      <div>
        <h1 class="text-3xl font-bold tracking-tight">Create Character</h1>
        <p class="text-muted-foreground">
          Create a new AI character for LoRA training
        </p>
      </div>

      <form @submit.prevent="createCharacter" class="space-y-6">
        <!-- Character Details -->
        <Card class="p-6">
          <h3 class="text-lg font-semibold mb-4">Character Details</h3>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium mb-2">Character Name</label>
              <Input
                v-model="form.name"
                placeholder="Enter character name (e.g., 'anime_girl', 'fantasy_warrior')"
                required
                pattern="[a-zA-Z0-9_-]+"
                title="Only letters, numbers, underscores, and hyphens allowed"
              />
              <p class="text-xs text-muted-foreground mt-1">
                Use only letters, numbers, underscores, and hyphens. This will be used for file naming.
              </p>
            </div>

            <!-- Dataset Selection -->
            <div>
              <label class="block text-sm font-medium mb-2">Training Dataset (Optional)</label>
              <select
                v-model="form.datasetId"
                class="w-full px-3 py-2 border border-input rounded-md"
                @change="onDatasetChange"
                :disabled="datasets.length === 0"
              >
                <option value="">{{ datasets.length === 0 ? 'No datasets available - use single image below' : 'Select a dataset or use single image' }}</option>
                <option
                  v-for="dataset in datasets"
                  :key="dataset.id"
                  :value="dataset.id"
                >
                  {{ dataset.name }} ({{ dataset.image_count }} images)
                </option>
              </select>
              <p class="text-xs text-muted-foreground mt-1">
                <span v-if="datasets.length === 0">No datasets found. </span>
                <router-link to="/datasets" class="text-primary hover:underline">Create a dataset</router-link> for better training results, or use a single reference image below.
              </p>
            </div>

            <!-- Trigger Word -->
            <div>
              <label class="block text-sm font-medium mb-2">Trigger Word</label>
              <Input
                v-model="form.triggerWord"
                placeholder="e.g., ohwx person, mychar"
                class="w-full"
              />
              <p class="text-xs text-muted-foreground mt-1">
                The word that will activate your character in prompts
              </p>
            </div>
          </div>
        </Card>

        <!-- Reference Image -->
        <Card class="p-6">
          <h3 class="text-lg font-semibold mb-4">Reference Image</h3>

          <div class="space-y-4">
            <!-- Image Selection -->
            <div v-if="!selectedImage">
              <div class="grid gap-4">
                <!-- Upload New Image -->
                <div
                  @drop="handleDrop"
                  @dragover.prevent
                  @dragenter.prevent
                  class="border-2 border-dashed border-border rounded-lg p-6 text-center transition-colors cursor-pointer hover:border-primary"
                  @click="triggerFileUpload"
                >
                  <input
                    ref="fileInput"
                    type="file"
                    accept="image/*"
                    @change="handleFileSelect"
                    class="hidden"
                  />

                  <Upload class="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                  <p class="font-medium">Upload Reference Image</p>
                  <p class="text-sm text-muted-foreground">
                    Drop an image here or click to browse
                  </p>
                </div>

                <!-- Or Select from Media Library -->
                <div class="text-center">
                  <p class="text-sm text-muted-foreground mb-3">Or select from your media library</p>
                  <Button
                    type="button"
                    variant="outline"
                    @click="openMediaLibrary"
                    :disabled="isLoadingMedia"
                  >
                    <Image class="mr-2 h-4 w-4" />
                    {{ isLoadingMedia ? 'Loading...' : `Choose from Library (${mediaFiles.length} images)` }}
                  </Button>
                  <p v-if="mediaFiles.length === 0 && !isLoadingMedia" class="text-xs text-muted-foreground mt-2">
                    No images in library. <router-link to="/media" class="text-primary hover:underline">Upload images first</router-link>
                  </p>
                </div>
              </div>
            </div>

            <!-- Selected Image Preview -->
            <div v-else class="space-y-4">
              <div class="relative inline-block">
                <img
                  :src="selectedImage.file_url || selectedImage.preview"
                  :alt="selectedImage.original_filename || selectedImage.name"
                  class="w-48 h-48 object-cover rounded-lg border"
                />
                <Button
                  @click="selectedImage = null"
                  class="absolute -top-2 -right-2"
                  size="sm"
                  variant="destructive"
                >
                  <X class="h-3 w-3" />
                </Button>
              </div>
              <div>
                <p class="font-medium">{{ selectedImage.original_filename || selectedImage.name }}</p>
                <p class="text-sm text-muted-foreground">
                  {{ selectedImage.width }}×{{ selectedImage.height }}
                  {{ selectedImage.file_size ? `• ${formatFileSize(selectedImage.file_size)}` : '' }}
                </p>
              </div>
            </div>
          </div>
        </Card>

        <!-- Model Configuration -->
        <Card class="p-6">
          <h3 class="text-lg font-semibold mb-4">Model Configuration</h3>
          <div class="grid md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-2">Base Model</label>
              <select
                v-model="form.modelConfig.baseModel"
                class="w-full px-3 py-2 border border-input rounded-md"
              >
                <option
                  v-for="model in availableModels.checkpoints"
                  :key="model.path"
                  :value="model.path"
                >
                  {{ model.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">VAE Model</label>
              <select
                v-model="form.modelConfig.vaeModel"
                class="w-full px-3 py-2 border border-input rounded-md"
              >
                <option
                  v-for="vae in availableModels.vaes"
                  :key="vae.path"
                  :value="vae.path"
                >
                  {{ vae.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Scheduler</label>
              <select
                v-model="form.modelConfig.scheduler"
                class="w-full px-3 py-2 border border-input rounded-md"
              >
                <option
                  v-for="scheduler in availableSchedulers"
                  :key="scheduler.value"
                  :value="scheduler.value"
                >
                  {{ scheduler.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Data Type</label>
              <select
                v-model="form.modelConfig.dtype"
                class="w-full px-3 py-2 border border-input rounded-md"
              >
                <option value="float16">Float16 (Recommended)</option>
                <option value="float32">Float32</option>
                <option value="bfloat16">BFloat16</option>
              </select>
            </div>
          </div>
        </Card>

        <!-- MV Adapter Configuration -->
        <Card class="p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold">MV Adapter (Multi-View)</h3>
            <label class="flex items-center space-x-2">
              <input
                v-model="form.mvAdapterConfig.enabled"
                type="checkbox"
                class="rounded border-input"
              />
              <span class="text-sm">Enable MV Adapter</span>
            </label>
          </div>

          <div v-if="form.mvAdapterConfig.enabled" class="grid md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-2">Number of Views</label>
              <Input
                v-model.number="form.mvAdapterConfig.numViews"
                type="number"
                min="4"
                max="12"
                class="w-full"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Guidance Scale</label>
              <Input
                v-model.number="form.mvAdapterConfig.guidanceScale"
                type="number"
                step="0.1"
                min="1.0"
                max="10.0"
                class="w-full"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Image Height</label>
              <Input
                v-model.number="form.mvAdapterConfig.height"
                type="number"
                min="512"
                max="1024"
                step="64"
                class="w-full"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Image Width</label>
              <Input
                v-model.number="form.mvAdapterConfig.width"
                type="number"
                min="512"
                max="1024"
                step="64"
                class="w-full"
              />
            </div>

            <div class="md:col-span-2">
              <label class="flex items-center space-x-2">
                <input
                  v-model="form.mvAdapterConfig.removeBackground"
                  type="checkbox"
                  class="rounded border-input"
                />
                <span class="text-sm">Remove Background</span>
              </label>
            </div>
          </div>
        </Card>

        <!-- Training Configuration -->
        <Card class="p-6">
          <h3 class="text-lg font-semibold mb-4">Training Configuration</h3>

          <div class="grid gap-4 md:grid-cols-2">
            <div>
              <label class="block text-sm font-medium mb-2">Training Steps</label>
              <Input
                v-model.number="form.steps"
                type="number"
                min="100"
                max="5000"
                step="100"
              />
              <p class="text-xs text-muted-foreground mt-1">
                More steps = better quality but longer training time (recommended: 800)
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Learning Rate</label>
              <Input
                v-model.number="form.learning_rate"
                type="number"
                min="0.0001"
                max="0.01"
                step="0.0001"
              />
              <p class="text-xs text-muted-foreground mt-1">
                Lower = more stable training (recommended: 0.0008)
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Training Dimension</label>
              <select v-model="form.train_dim" class="w-full h-10 px-3 py-2 border border-input rounded-md bg-background">
                <option value="512">512x512 (Faster)</option>
                <option value="768">768x768 (Balanced)</option>
                <option value="1024">1024x1024 (Higher Quality)</option>
              </select>
              <p class="text-xs text-muted-foreground mt-1">
                Higher resolution = better quality but slower training
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">LoRA Rank</label>
              <Input
                v-model.number="form.rank_dim"
                type="number"
                min="4"
                max="32"
                step="4"
              />
              <p class="text-xs text-muted-foreground mt-1">
                Higher rank = more detailed but larger model (recommended: 8)
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Batch Size</label>
              <Input
                v-model.number="form.batch_size"
                type="number"
                min="1"
                max="4"
              />
              <p class="text-xs text-muted-foreground mt-1">
                Higher batch size requires more VRAM
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">PuLID-Flux Images</label>
              <Input
                v-model.number="form.pulidflux_images"
                type="number"
                min="0"
                max="10"
              />
              <p class="text-xs text-muted-foreground mt-1">
                Additional synthetic images for training (0 = disabled)
              </p>
            </div>
          </div>
        </Card>

        <!-- Advanced Training Configuration -->
        <AdvancedTrainingConfig
          :config="form.advancedConfig"
          :available-optimizers="availableOptimizers"
          :available-trainers="availableTrainers"
          :available-models="availableModels"
          @update:config="form.advancedConfig = $event"
          @update:selected-trainer="selectedTrainer = $event"
        />

        <!-- Configuration Summary -->
        <ModelConfigSummary :config="form" />

        <!-- Actions -->
        <div class="flex justify-end space-x-3">
          <Button type="button" variant="outline" @click="$router.push('/characters')">
            Cancel
          </Button>
          <Button type="submit" :disabled="!canCreate || isCreating">
            <Zap class="mr-2 h-4 w-4" />
            {{ isCreating ? 'Creating...' : 'Create Character' }}
          </Button>
        </div>
      </form>
    </div>

    <!-- Media Library Modal -->
    <div
      v-if="showMediaLibrary"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      @click="showMediaLibrary = false"
    >
      <div
        class="bg-background rounded-lg max-w-4xl max-h-[80vh] overflow-auto w-full"
        @click.stop
      >
        <div class="p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold">Select Reference Image</h3>
            <Button @click="showMediaLibrary = false" variant="ghost" size="sm">
              <X class="h-4 w-4" />
            </Button>
          </div>

          <div v-if="mediaFiles.length === 0" class="text-center py-8">
            <p class="text-muted-foreground">No images in your media library</p>
            <Button @click="showMediaLibrary = false; $router.push('/media')" class="mt-2">
              Upload Images
            </Button>
          </div>

          <div v-else class="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <div
              v-for="file in mediaFiles"
              :key="file.filename"
              class="aspect-square bg-muted rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary transition-all"
              @click="selectImageFromLibrary(file)"
            >
              <img
                :src="file.file_url"
                :alt="file.original_filename"
                class="w-full h-full object-cover"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'vue-toastification'
import { Upload, Image, X, Zap } from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import AdvancedTrainingConfig from '@/components/training/AdvancedTrainingConfig.vue'
import ModelConfigSummary from '@/components/training/ModelConfigSummary.vue'
import { charactersApi, mediaApi, datasetApi, api, type MediaFile, type Dataset } from '@/services/api'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const form = ref({
  name: '',
  datasetId: '',
  triggerWord: '',
  steps: 800,
  batch_size: 1,
  learning_rate: 0.0008,
  train_dim: 512,
  rank_dim: 8,
  pulidflux_images: 0,

  // Model configuration
  modelConfig: {
    baseModel: 'RunDiffusion/Juggernaut-XL-v9',
    vaeModel: 'madebyollin/sdxl-vae-fp16-fix',
    unetModel: null,
    adapterPath: 'huanngzh/mv-adapter',
    scheduler: 'ddpm',
    dtype: 'float16'
  },

  // MV Adapter configuration
  mvAdapterConfig: {
    enabled: false,
    numViews: 6,
    height: 768,
    width: 768,
    guidanceScale: 3.0,
    referenceConditioningScale: 1.0,
    azimuthDegrees: [0, 45, 90, 180, 270, 315],
    removeBackground: true
  },

  // Advanced configuration
  advancedConfig: {
    optimizer: 'adamw',
    weightDecay: 0.01,
    lrScheduler: 'constant',
    gradientCheckpointing: true,
    trainTextEncoder: false,
    noiseScheduler: 'ddpm',
    gradientAccumulation: 1,
    mixedPrecision: 'fp16',
    saveEvery: 250,
    maxSaves: 5
  },

  // ComfyUI model selection
  comfyuiCheckpoint: null,
  comfyuiVae: null,
  comfyuiLora: null
})

const selectedImage = ref<MediaFile | File | null>(null)
const showMediaLibrary = ref(false)
const mediaFiles = ref<MediaFile[]>([])
const datasets = ref<Dataset[]>([])
const isCreating = ref(false)
const isLoadingMedia = ref(false)
const fileInput = ref<HTMLInputElement>()

// Model and configuration data
const availableModels = ref({
  checkpoints: [],
  vaes: [],
  loras: [],
  controlnets: [],
  adapters: []
})
const availableSchedulers = ref([])
const availableOptimizers = ref([])
const availableTrainers = ref([])
const selectedTrainer = ref('lora')

const canCreate = computed(() => {
  const hasName = form.value.name.trim().length > 0
  const hasTriggerWord = form.value.triggerWord.trim().length > 0
  const hasImageOrDataset = selectedImage.value || form.value.datasetId
  const validParams = validateTrainingParameters()

  // Debug logging
  console.log('[CreateCharacter] canCreate check:', {
    hasName,
    hasTriggerWord,
    hasImageOrDataset: !!hasImageOrDataset,
    validParams,
    selectedImage: selectedImage.value,
    datasetId: form.value.datasetId
  })

  return hasName && hasTriggerWord && hasImageOrDataset && validParams
})

const validateTrainingParameters = () => {
  // Validate basic parameters (convert to numbers in case they're strings from select)
  const steps = Number(form.value.steps)
  const learningRate = Number(form.value.learning_rate)
  const batchSize = Number(form.value.batch_size)
  const rankDim = Number(form.value.rank_dim)
  const trainDim = Number(form.value.train_dim)

  if (isNaN(steps) || steps < 100 || steps > 10000) return false
  if (isNaN(learningRate) || learningRate < 0.0001 || learningRate > 0.01) return false
  if (isNaN(batchSize) || batchSize < 1 || batchSize > 16) return false
  if (isNaN(rankDim) || rankDim < 4 || rankDim > 256) return false
  if (isNaN(trainDim) || trainDim < 256 || trainDim > 2048) return false

  // Validate MV Adapter if enabled
  if (form.value.mvAdapterConfig.enabled) {
    if (form.value.mvAdapterConfig.numViews < 4 || form.value.mvAdapterConfig.numViews > 12) return false
    if (form.value.mvAdapterConfig.guidanceScale < 1.0 || form.value.mvAdapterConfig.guidanceScale > 20.0) return false
    if (form.value.mvAdapterConfig.height < 512 || form.value.mvAdapterConfig.height > 2048) return false
    if (form.value.mvAdapterConfig.width < 512 || form.value.mvAdapterConfig.width > 2048) return false
  }

  return true
}

const loadMediaFiles = async () => {
  isLoadingMedia.value = true
  try {
    console.log('[CreateCharacter] Loading media files...')
    const response = await mediaApi.list()
    console.log('[CreateCharacter] Media files loaded:', response)
    mediaFiles.value = response.files
    console.log('[CreateCharacter] mediaFiles.value set to:', mediaFiles.value)
  } catch (error) {
    console.error('[CreateCharacter] Failed to load media files:', error)
  } finally {
    isLoadingMedia.value = false
  }
}

const openMediaLibrary = () => {
  console.log('[CreateCharacter] Opening media library, files available:', mediaFiles.value.length)
  if (mediaFiles.value.length === 0) {
    toast.warning('No images in library. Please upload images first.')
    return
  }
  showMediaLibrary.value = true
}

const loadDatasets = async () => {
  try {
    console.log('[CreateCharacter] Loading datasets...')
    const response = await datasetApi.getDatasets()
    console.log('[CreateCharacter] Datasets loaded:', response)
    datasets.value = response.datasets.filter(d => d.status === 'ready')
    console.log('[CreateCharacter] Ready datasets:', datasets.value)
  } catch (error) {
    console.error('[CreateCharacter] Failed to load datasets:', error)
    toast.error('Failed to load datasets')
  }
}

const loadModelsAndConfig = async () => {
  try {
    // Load available models
    const modelsResponse = await api.get('/models')
    availableModels.value = modelsResponse.data

    // Load schedulers
    const schedulersResponse = await api.get('/models/schedulers')
    availableSchedulers.value = schedulersResponse.data.schedulers

    // Load optimizers
    const optimizersResponse = await api.get('/models/optimizers')
    availableOptimizers.value = optimizersResponse.data.optimizers

    // Load trainers
    const trainersResponse = await api.get('/models/trainers')
    availableTrainers.value = trainersResponse.data.trainers

  } catch (error: any) {
    console.error('Failed to load models and configuration:', error)
    toast.error('Failed to load model configuration')
  }
}

const onDatasetChange = async () => {
  if (form.value.datasetId) {
    try {
      const dataset = await datasetApi.getDataset(parseInt(form.value.datasetId))
      form.value.triggerWord = dataset.trigger_word
      // Clear selected image since we're using a dataset
      selectedImage.value = null
    } catch (error) {
      toast.error('Failed to load dataset details')
    }
  }
}

const triggerFileUpload = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    const file = target.files[0]
    // Create preview URL for the file
    const preview = URL.createObjectURL(file)
    selectedImage.value = Object.assign(file, { preview })
  }
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    const file = event.dataTransfer.files[0]
    const preview = URL.createObjectURL(file)
    selectedImage.value = Object.assign(file, { preview })
  }
}

const selectImageFromLibrary = (file: MediaFile) => {
  console.log('[CreateCharacter] Selecting image from library:', file)
  selectedImage.value = file
  showMediaLibrary.value = false
  console.log('[CreateCharacter] selectedImage set to:', selectedImage.value)
}

const createCharacter = async () => {
  console.log('[CreateCharacter] createCharacter called, canCreate:', canCreate.value)

  if (!canCreate.value) {
    console.log('[CreateCharacter] Cannot create - validation failed')
    // Show which validation is failing
    const hasName = form.value.name.trim().length > 0
    const hasTriggerWord = form.value.triggerWord.trim().length > 0
    const hasImageOrDataset = selectedImage.value || form.value.datasetId
    const validParams = validateTrainingParameters()

    if (!hasName) toast.error('Character name is required')
    else if (!hasTriggerWord) toast.error('Trigger word is required')
    else if (!hasImageOrDataset) toast.error('Please select an image or dataset')
    else if (!validParams) toast.error('Invalid training parameters')
    return
  }

  isCreating.value = true
  try {
    let imagePath = ''

    // If selected image is a File (newly uploaded), upload it first
    if (selectedImage.value instanceof File) {
      console.log('[CreateCharacter] Uploading new file...')
      const uploadedFile = await mediaApi.upload(selectedImage.value)
      imagePath = uploadedFile.file_path
      console.log('[CreateCharacter] File uploaded, path:', imagePath)
    } else if (selectedImage.value) {
      // Use existing media file path
      imagePath = (selectedImage.value as MediaFile).file_path
      console.log('[CreateCharacter] Using existing file path:', imagePath)
    }

    console.log('[CreateCharacter] Creating character with:', { name: form.value.name, imagePath })

    // Create character
    const character = await charactersApi.create({
      name: form.value.name,
      input_image_path: imagePath
    })

    console.log('[CreateCharacter] Character created:', character)
    toast.success('Character created successfully!')
    router.push(`/characters/${character.id}`)
  } catch (error: any) {
    console.error('[CreateCharacter] Error creating character:', error)
    toast.error(error.response?.data?.detail || 'Failed to create character')
  } finally {
    isCreating.value = false
  }
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Debug watcher for media library modal
watch(showMediaLibrary, (newVal) => {
  if (newVal) {
    console.log('[CreateCharacter] Media library modal opened')
    console.log('[CreateCharacter] Available media files:', mediaFiles.value)
    console.log('[CreateCharacter] Media files count:', mediaFiles.value.length)
  }
})

onMounted(async () => {
  console.log('[CreateCharacter] Component mounted, loading data...')
  // Load all data in parallel
  await Promise.all([
    loadMediaFiles(),
    loadDatasets(),
    loadModelsAndConfig()
  ])

  // Check if dataset is pre-selected via query parameter
  const datasetId = route.query.dataset as string
  if (datasetId && datasets.value.find(d => d.id === parseInt(datasetId))) {
    form.value.datasetId = datasetId
    await onDatasetChange()
  }
})
</script>
