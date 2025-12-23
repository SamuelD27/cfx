<template>
  <AppLayout>
    <div class="space-y-6">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-bold tracking-tight">Media Library</h1>
          <p class="text-muted-foreground">
            Upload and manage images for character training
          </p>
        </div>
        <div class="flex space-x-2">
          <Button @click="triggerFileUpload" variant="outline">
            <Upload class="mr-2 h-4 w-4" />
            Upload Images
          </Button>
          <Button @click="showDatasetModal = true">
            <FolderPlus class="mr-2 h-4 w-4" />
            Create Dataset
          </Button>
        </div>
      </div>

      <!-- Upload Area -->
      <Card class="p-6">
        <div
          @drop="handleDrop"
          @dragover.prevent
          @dragenter.prevent
          class="border-2 border-dashed border-border rounded-lg p-8 text-center transition-colors"
          :class="{ 'border-primary bg-primary/5': isDragging }"
        >
          <input
            ref="fileInput"
            type="file"
            multiple
            accept="image/*"
            @change="handleFileSelect"
            class="hidden"
          />

          <div class="space-y-4">
            <div class="mx-auto w-12 h-12 bg-muted rounded-lg flex items-center justify-center">
              <Upload class="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <p class="text-lg font-medium">Drop images here or click to upload</p>
              <p class="text-sm text-muted-foreground">
                Supports JPG, PNG, WebP up to 50MB each
              </p>
            </div>
          </div>
        </div>
      </Card>

      <!-- Upload Progress -->
      <div v-if="uploadQueue.length > 0" class="space-y-2">
        <h3 class="text-lg font-semibold">Uploading Files</h3>
        <div v-for="upload in uploadQueue" :key="upload.id" class="flex items-center space-x-3 p-3 bg-muted rounded-lg">
          <div class="flex-1">
            <p class="text-sm font-medium">{{ upload.file.name }}</p>
            <div class="w-full bg-background rounded-full h-2 mt-1">
              <div
                class="bg-primary h-2 rounded-full transition-all duration-300"
                :style="{ width: `${upload.progress}%` }"
              ></div>
            </div>
          </div>
          <div class="text-sm text-muted-foreground">{{ upload.progress }}%</div>
        </div>
      </div>

      <!-- Media Grid -->
      <div v-if="mediaFiles.length > 0">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">Your Images ({{ mediaFiles.length }})</h3>
          <div class="flex items-center space-x-2">
            <Button @click="viewMode = 'grid'" :variant="viewMode === 'grid' ? 'default' : 'outline'" size="sm">
              <Grid3X3 class="h-4 w-4" />
            </Button>
            <Button @click="viewMode = 'list'" :variant="viewMode === 'list' ? 'default' : 'outline'" size="sm">
              <List class="h-4 w-4" />
            </Button>
          </div>
        </div>

        <!-- Grid View -->
        <div v-if="viewMode === 'grid'" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
          <div
            v-for="file in mediaFiles"
            :key="file.filename"
            class="group relative aspect-square bg-muted rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary transition-all"
            @click="selectedFile = file"
          >
            <img
              :src="file.file_url"
              :alt="file.original_filename"
              class="w-full h-full object-cover"
              loading="lazy"
            />
            <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
            <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button @click.stop="deleteFile(file)" size="sm" variant="destructive">
                <Trash2 class="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>

        <!-- List View -->
        <div v-else class="space-y-2">
          <div
            v-for="file in mediaFiles"
            :key="file.filename"
            class="flex items-center space-x-4 p-3 bg-card rounded-lg border hover:bg-accent transition-colors cursor-pointer"
            @click="selectedFile = file"
          >
            <img
              :src="file.file_url"
              :alt="file.original_filename"
              class="w-12 h-12 object-cover rounded"
              loading="lazy"
            />
            <div class="flex-1 min-w-0">
              <p class="font-medium truncate">{{ file.original_filename }}</p>
              <p class="text-sm text-muted-foreground">
                {{ formatFileSize(file.file_size) }} • {{ file.width }}×{{ file.height }}
              </p>
            </div>
            <Button @click.stop="deleteFile(file)" size="sm" variant="ghost">
              <Trash2 class="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="!isLoading" class="text-center py-12">
        <div class="mx-auto w-16 h-16 bg-muted rounded-lg flex items-center justify-center mb-4">
          <Image class="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 class="text-lg font-semibold mb-2">No images uploaded yet</h3>
        <p class="text-muted-foreground mb-4">
          Upload your first image to get started with character training
        </p>
        <Button @click="triggerFileUpload">
          <Upload class="mr-2 h-4 w-4" />
          Upload Images
        </Button>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
        <p class="text-muted-foreground">Loading images...</p>
      </div>
    </div>

    <!-- Image Detail Modal -->
    <div
      v-if="selectedFile"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      @click="selectedFile = null"
    >
      <div
        class="bg-background rounded-lg max-w-4xl max-h-[90vh] overflow-auto"
        @click.stop
      >
        <div class="p-6">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-lg font-semibold">{{ selectedFile.original_filename }}</h3>
              <p class="text-sm text-muted-foreground">
                {{ formatFileSize(selectedFile.file_size) }} • {{ selectedFile.width }}×{{ selectedFile.height }}
              </p>
            </div>
            <Button @click="selectedFile = null" variant="ghost" size="sm">
              <X class="h-4 w-4" />
            </Button>
          </div>

          <img
            :src="selectedFile.file_url"
            :alt="selectedFile.original_filename"
            class="w-full max-h-96 object-contain rounded-lg mb-4"
          />

          <div class="flex justify-end space-x-2">
            <Button @click="downloadFile(selectedFile)" variant="outline">
              <Download class="mr-2 h-4 w-4" />
              Download
            </Button>
            <Button @click="deleteFile(selectedFile)" variant="destructive">
              <Trash2 class="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Dataset Creation Modal -->
    <DatasetModal
      v-if="showDatasetModal"
      :files="mediaFiles"
      @close="showDatasetModal = false"
      @created="handleDatasetCreated"
    />
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import {
  Upload, Image, Grid3X3, List, Trash2, X, Download, FolderPlus
} from 'lucide-vue-next'
import AppLayout from '@/components/layout/AppLayout.vue'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'
import DatasetModal from '@/components/media/DatasetModal.vue'
import { mediaApi, type MediaFile } from '@/services/api'

const toast = useToast()

const mediaFiles = ref<MediaFile[]>([])
const selectedFile = ref<MediaFile | null>(null)
const isLoading = ref(false)
const isDragging = ref(false)
const viewMode = ref<'grid' | 'list'>('grid')
const fileInput = ref<HTMLInputElement>()
const showDatasetModal = ref(false)

interface UploadItem {
  id: string
  file: File
  progress: number
}

const uploadQueue = ref<UploadItem[]>([])

const loadMediaFiles = async () => {
  isLoading.value = true
  try {
    const response = await mediaApi.list()
    mediaFiles.value = response.files
  } catch (error: any) {
    toast.error('Failed to load media files')
  } finally {
    isLoading.value = false
  }
}

const triggerFileUpload = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    uploadFiles(Array.from(target.files))
  }
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  isDragging.value = false

  if (event.dataTransfer?.files) {
    uploadFiles(Array.from(event.dataTransfer.files))
  }
}

const uploadFiles = async (files: File[]) => {
  for (const file of files) {
    const uploadItem: UploadItem = {
      id: Math.random().toString(36).substr(2, 9),
      file,
      progress: 0
    }

    uploadQueue.value.push(uploadItem)

    try {
      // Simulate progress for now - in real implementation, you'd track actual upload progress
      const progressInterval = setInterval(() => {
        uploadItem.progress += 10
        if (uploadItem.progress >= 90) {
          clearInterval(progressInterval)
        }
      }, 100)

      const uploadedFile = await mediaApi.upload(file)

      clearInterval(progressInterval)
      uploadItem.progress = 100

      // Remove from queue after a short delay
      setTimeout(() => {
        uploadQueue.value = uploadQueue.value.filter(item => item.id !== uploadItem.id)
      }, 1000)

      // Add to media files
      mediaFiles.value.unshift(uploadedFile)
      toast.success(`${file.name} uploaded successfully!`)

    } catch (error: any) {
      uploadQueue.value = uploadQueue.value.filter(item => item.id !== uploadItem.id)
      toast.error(`Failed to upload ${file.name}`)
    }
  }
}

const deleteFile = async (file: MediaFile) => {
  try {
    await mediaApi.delete(file.filename)
    mediaFiles.value = mediaFiles.value.filter(f => f.filename !== file.filename)
    selectedFile.value = null
    toast.success('File deleted successfully')
  } catch (error: any) {
    toast.error('Failed to delete file')
  }
}

const downloadFile = (file: MediaFile) => {
  const link = document.createElement('a')
  link.href = file.file_url
  link.download = file.original_filename
  link.click()
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const handleDatasetCreated = (datasetName: string) => {
  showDatasetModal.value = false
  toast.success(`Dataset "${datasetName}" created successfully!`)
  loadMediaFiles() // Refresh the file list
}

onMounted(() => {
  loadMediaFiles()
})
</script>
