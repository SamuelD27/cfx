<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
    <div class="bg-background rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
      <div class="p-6 border-b border-border">
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-bold">Create Dataset</h2>
          <Button @click="$emit('close')" variant="ghost" size="sm">
            <X class="h-4 w-4" />
          </Button>
        </div>
        <p class="text-muted-foreground mt-2">
          Select images and configure dataset settings for character training
        </p>
      </div>

      <div class="p-6 overflow-auto max-h-[calc(90vh-200px)]">
        <!-- Dataset Configuration -->
        <div class="grid md:grid-cols-2 gap-6 mb-6">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium mb-2">Dataset Name</label>
              <Input
                v-model="datasetName"
                placeholder="Enter dataset name"
                class="w-full"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Trigger Word</label>
              <Input
                v-model="triggerWord"
                placeholder="e.g., ohwx person, mychar"
                class="w-full"
              />
              <p class="text-xs text-muted-foreground mt-1">
                The word that will activate your character in prompts
              </p>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Caption Template</label>
              <textarea
                v-model="captionTemplate"
                placeholder="a photo of {trigger} person"
                class="w-full min-h-[100px] px-3 py-2 border border-input rounded-md resize-none"
              />
              <p class="text-xs text-muted-foreground mt-1">
                Use {trigger} as placeholder for the trigger word
              </p>
            </div>

            <div>
              <label class="flex items-center space-x-2">
                <input
                  v-model="autoCaption"
                  type="checkbox"
                  class="rounded border-input"
                />
                <span class="text-sm">Auto-generate captions using AI</span>
              </label>
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium mb-2">Image Processing</label>
              <div class="space-y-2">
                <label class="flex items-center space-x-2">
                  <input
                    v-model="resizeImages"
                    type="checkbox"
                    class="rounded border-input"
                  />
                  <span class="text-sm">Resize images to 512x512</span>
                </label>
                <label class="flex items-center space-x-2">
                  <input
                    v-model="cropImages"
                    type="checkbox"
                    class="rounded border-input"
                  />
                  <span class="text-sm">Smart crop faces</span>
                </label>
                <label class="flex items-center space-x-2">
                  <input
                    v-model="flipImages"
                    type="checkbox"
                    class="rounded border-input"
                  />
                  <span class="text-sm">Add horizontal flips for augmentation</span>
                </label>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2">Quality Filter</label>
              <select
                v-model="qualityFilter"
                class="w-full px-3 py-2 border border-input rounded-md"
              >
                <option value="none">No filtering</option>
                <option value="basic">Basic quality check</option>
                <option value="strict">Strict quality check</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Image Selection -->
        <div class="mb-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold">Select Images ({{ selectedImages.length }}/{{ files.length }})</h3>
            <div class="flex space-x-2">
              <Button @click="selectAll" variant="outline" size="sm">
                Select All
              </Button>
              <Button @click="selectNone" variant="outline" size="sm">
                Clear Selection
              </Button>
            </div>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div
              v-for="file in files"
              :key="file.filename"
              class="relative group cursor-pointer"
              @click="toggleImageSelection(file)"
            >
              <div
                class="aspect-square rounded-lg overflow-hidden border-2 transition-all"
                :class="[
                  selectedImages.includes(file.filename)
                    ? 'border-primary ring-2 ring-primary/20'
                    : 'border-border hover:border-primary/50'
                ]"
              >
                <img
                  :src="file.file_url"
                  :alt="file.original_filename"
                  class="w-full h-full object-cover"
                />
              </div>
              
              <!-- Selection indicator -->
              <div
                v-if="selectedImages.includes(file.filename)"
                class="absolute top-2 right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center"
              >
                <Check class="h-4 w-4 text-primary-foreground" />
              </div>
              
              <!-- File name -->
              <p class="text-xs text-muted-foreground mt-1 truncate">
                {{ file.original_filename }}
              </p>
            </div>
          </div>
        </div>

        <!-- Multi-file Upload -->
        <div class="mb-6">
          <h3 class="text-lg font-semibold mb-4">Add More Images</h3>
          <div
            @drop="handleDrop"
            @dragover.prevent
            @dragenter.prevent
            class="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-primary/50 transition-colors"
          >
            <Upload class="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p class="text-lg font-medium mb-2">Drop images here or click to browse</p>
            <p class="text-muted-foreground mb-4">Support for JPG, PNG, WebP files</p>
            <Button @click="triggerFileUpload" variant="outline">
              <Upload class="mr-2 h-4 w-4" />
              Browse Files
            </Button>
            <input
              ref="fileInput"
              type="file"
              multiple
              accept="image/*"
              class="hidden"
              @change="handleFileSelect"
            />
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="p-6 border-t border-border">
        <div class="flex justify-between items-center">
          <div class="text-sm text-muted-foreground">
            {{ selectedImages.length }} images selected
          </div>
          <div class="flex space-x-3">
            <Button @click="$emit('close')" variant="outline">
              Cancel
            </Button>
            <Button
              @click="createDataset"
              :disabled="!canCreateDataset"
              :loading="isCreating"
            >
              <FolderPlus class="mr-2 h-4 w-4" />
              Create Dataset
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'vue-toastification'
import {
  X, Upload, Check, FolderPlus
} from 'lucide-vue-next'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import { mediaApi, datasetApi, type MediaFile, type CreateDatasetRequest } from '@/services/api'

interface Props {
  files: MediaFile[]
}

interface Emits {
  (e: 'close'): void
  (e: 'created', datasetName: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const toast = useToast()

// Dataset configuration
const datasetName = ref('')
const triggerWord = ref('')
const captionTemplate = ref('a photo of {trigger} person')
const autoCaption = ref(true)
const resizeImages = ref(true)
const cropImages = ref(true)
const flipImages = ref(false)
const qualityFilter = ref('basic')

// Image selection
const selectedImages = ref<string[]>([])
const isCreating = ref(false)
const fileInput = ref<HTMLInputElement>()

const canCreateDataset = computed(() => {
  return datasetName.value.trim() && 
         triggerWord.value.trim() && 
         selectedImages.value.length > 0
})

const toggleImageSelection = (file: MediaFile) => {
  const index = selectedImages.value.indexOf(file.filename)
  if (index > -1) {
    selectedImages.value.splice(index, 1)
  } else {
    selectedImages.value.push(file.filename)
  }
}

const selectAll = () => {
  selectedImages.value = props.files.map(f => f.filename)
}

const selectNone = () => {
  selectedImages.value = []
}

const triggerFileUpload = () => {
  fileInput.value?.click()
}

const handleFileSelect = async (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    await uploadFiles(Array.from(target.files))
  }
}

const handleDrop = async (event: DragEvent) => {
  event.preventDefault()
  if (event.dataTransfer?.files) {
    await uploadFiles(Array.from(event.dataTransfer.files))
  }
}

const uploadFiles = async (filesToUpload: File[]) => {
  for (const file of filesToUpload) {
    try {
      await mediaApi.upload(file)
      toast.success(`Uploaded ${file.name}`)
    } catch (error) {
      toast.error(`Failed to upload ${file.name}`)
    }
  }
  // Emit event to refresh parent file list
  emit('created', 'refresh')
}

const createDataset = async () => {
  if (!canCreateDataset.value) return

  isCreating.value = true
  try {
    const datasetConfig: CreateDatasetRequest = {
      name: datasetName.value.trim(),
      trigger_word: triggerWord.value.trim(),
      caption_template: captionTemplate.value,
      auto_caption: autoCaption.value,
      resize_images: resizeImages.value,
      crop_images: cropImages.value,
      flip_images: flipImages.value,
      quality_filter: qualityFilter.value,
      selected_images: selectedImages.value
    }

    await datasetApi.createDataset(datasetConfig)

    toast.success(`Dataset "${datasetName.value}" created successfully!`)
    emit('created', datasetName.value)
  } catch (error: any) {
    const message = error.response?.data?.detail || 'Failed to create dataset'
    toast.error(message)
  } finally {
    isCreating.value = false
  }
}
</script>
