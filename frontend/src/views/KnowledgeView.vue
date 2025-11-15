<template>
  <div class="flex h-full gap-6">
    <!-- Left Sidebar: Categories -->
    <div class="w-64 flex-shrink-0 bg-surface border border-border-color rounded-lg p-4">
      <h3 class="text-lg font-bold text-text-primary mb-4">Categories</h3>
      <div class="space-y-1">
        <button
          v-for="category in categories"
          :key="category.id"
          @click="selectedCategory = category.id"
          :class="[
            'w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors text-left',
            selectedCategory === category.id
              ? 'bg-primary/20 text-primary'
              : 'text-text-primary hover:bg-background-dark'
          ]"
        >
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-sm">{{ category.icon }}</span>
            <span class="text-sm font-semibold">{{ category.name }}</span>
          </div>
          <span class="text-xs px-2 py-0.5 rounded-full bg-surface-light text-text-secondary">
            {{ category.count }}
          </span>
        </button>
      </div>

      <div class="mt-6 pt-6 border-t border-border-color">
        <button class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-primary text-background-dark hover:bg-primary/90 transition-colors text-sm font-semibold">
          <span class="material-symbols-outlined text-sm">create_new_folder</span>
          New Category
        </button>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-text-primary mb-1">Knowledge Base</h1>
          <p class="text-sm text-text-secondary">
            {{ documents.filter(d => selectedCategory === 'all' || d.category === selectedCategory).length }} documents
          </p>
        </div>
        <div class="flex items-center gap-3">
          <div class="relative">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search documents..."
              class="w-64 px-4 py-2 pl-10 rounded-lg bg-surface border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors"
            />
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">
              search
            </span>
          </div>
          <button
            @click="showUploadModal = true"
            class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-background-dark font-semibold hover:bg-primary/90 transition-colors"
          >
            <span class="material-symbols-outlined">cloud_upload</span>
            Upload
          </button>
        </div>
      </div>

      <!-- Documents List -->
      <div class="flex-1 bg-surface border border-border-color rounded-lg overflow-hidden">
        <div class="overflow-y-auto h-full">
          <table class="w-full">
            <thead class="bg-background-dark sticky top-0">
              <tr>
                <th class="text-left px-6 py-3 text-xs font-semibold text-text-secondary uppercase">Name</th>
                <th class="text-left px-6 py-3 text-xs font-semibold text-text-secondary uppercase">Type</th>
                <th class="text-left px-6 py-3 text-xs font-semibold text-text-secondary uppercase">Size</th>
                <th class="text-left px-6 py-3 text-xs font-semibold text-text-secondary uppercase">Uploaded</th>
                <th class="text-left px-6 py-3 text-xs font-semibold text-text-secondary uppercase">Status</th>
                <th class="text-right px-6 py-3 text-xs font-semibold text-text-secondary uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="doc in filteredDocuments"
                :key="doc.id"
                class="border-t border-border-color hover:bg-background-dark transition-colors"
              >
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                      <span class="material-symbols-outlined text-primary">{{ getFileIcon(doc.type) }}</span>
                    </div>
                    <div>
                      <p class="font-semibold text-text-primary text-sm">{{ doc.name }}</p>
                      <p class="text-xs text-text-secondary">{{ doc.description }}</p>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span class="text-xs px-2 py-1 rounded bg-surface-light text-text-secondary uppercase">
                    {{ doc.type }}
                  </span>
                </td>
                <td class="px-6 py-4 text-sm text-text-secondary">{{ doc.size }}</td>
                <td class="px-6 py-4 text-sm text-text-secondary">{{ doc.uploadedAt }}</td>
                <td class="px-6 py-4">
                  <span
                    :class="[
                      'text-xs px-2 py-1 rounded font-semibold',
                      doc.status === 'processed' ? 'bg-accent-green/20 text-accent-green' :
                      doc.status === 'processing' ? 'bg-accent-yellow/20 text-accent-yellow' :
                      'bg-accent-red/20 text-accent-red'
                    ]"
                  >
                    {{ doc.status }}
                  </span>
                </td>
                <td class="px-6 py-4">
                  <div class="flex items-center justify-end gap-2">
                    <button class="p-2 rounded hover:bg-surface transition-colors" title="View">
                      <span class="material-symbols-outlined text-sm text-text-secondary">visibility</span>
                    </button>
                    <button class="p-2 rounded hover:bg-surface transition-colors" title="Download">
                      <span class="material-symbols-outlined text-sm text-text-secondary">download</span>
                    </button>
                    <button class="p-2 rounded hover:bg-surface transition-colors" title="Delete">
                      <span class="material-symbols-outlined text-sm text-text-secondary">delete</span>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Empty State -->
          <div v-if="filteredDocuments.length === 0" class="flex flex-col items-center justify-center h-64">
            <span class="material-symbols-outlined text-6xl text-text-secondary mb-4">folder_open</span>
            <h3 class="text-lg font-bold text-text-primary mb-2">No documents found</h3>
            <p class="text-sm text-text-secondary mb-4">Upload documents to get started</p>
            <button
              @click="showUploadModal = true"
              class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-background-dark font-semibold hover:bg-primary/90 transition-colors"
            >
              <span class="material-symbols-outlined">cloud_upload</span>
              Upload Document
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Upload Modal -->
    <div
      v-if="showUploadModal"
      class="fixed inset-0 bg-background-dark/80 flex items-center justify-center z-50"
      @click.self="showUploadModal = false"
    >
      <div class="bg-surface border border-border-color rounded-lg p-6 max-w-lg w-full mx-4">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-bold text-text-primary">Upload Documents</h2>
          <button
            @click="showUploadModal = false"
            class="p-1 rounded hover:bg-background-dark transition-colors"
          >
            <span class="material-symbols-outlined text-text-secondary">close</span>
          </button>
        </div>

        <div class="space-y-6">
          <!-- Category Selection -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">Category</label>
            <select
              v-model="uploadForm.category"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
            >
              <option v-for="cat in categories.filter(c => c.id !== 'all')" :key="cat.id" :value="cat.id">
                {{ cat.name }}
              </option>
            </select>
          </div>

          <!-- File Upload -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">Files</label>
            <div
              class="border-2 border-dashed border-border-color rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer"
              @click="triggerFileUpload"
            >
              <span class="material-symbols-outlined text-4xl text-text-secondary mb-2">cloud_upload</span>
              <p class="text-sm text-text-primary font-semibold mb-1">
                Click to upload or drag and drop
              </p>
              <p class="text-xs text-text-secondary">
                PDF, DOCX, XLSX, CSV, TXT (Max 100MB)
              </p>
              <input
                ref="fileInput"
                type="file"
                multiple
                accept=".pdf,.docx,.xlsx,.csv,.txt"
                class="hidden"
                @change="handleFileSelect"
              />
            </div>

            <!-- Selected Files -->
            <div v-if="uploadForm.files.length > 0" class="mt-4 space-y-2">
              <div
                v-for="(file, index) in uploadForm.files"
                :key="index"
                class="flex items-center justify-between p-3 rounded-lg bg-background-dark border border-border-color"
              >
                <div class="flex items-center gap-3">
                  <span class="material-symbols-outlined text-primary">description</span>
                  <div>
                    <p class="text-sm font-semibold text-text-primary">{{ file.name }}</p>
                    <p class="text-xs text-text-secondary">{{ formatFileSize(file.size) }}</p>
                  </div>
                </div>
                <button
                  @click="removeFile(index)"
                  class="text-text-secondary hover:text-accent-red transition-colors"
                >
                  <span class="material-symbols-outlined">close</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-3 pt-4">
            <button
              @click="showUploadModal = false"
              class="flex-1 px-4 py-3 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors font-semibold"
            >
              Cancel
            </button>
            <button
              @click="uploadFiles"
              :disabled="uploadForm.files.length === 0"
              :class="[
                'flex-1 px-4 py-3 rounded-lg font-semibold transition-colors',
                uploadForm.files.length > 0
                  ? 'bg-primary text-background-dark hover:bg-primary/90'
                  : 'bg-surface text-text-secondary cursor-not-allowed'
              ]"
            >
              Upload {{ uploadForm.files.length }} file{{ uploadForm.files.length !== 1 ? 's' : '' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const selectedCategory = ref('all');
const searchQuery = ref('');
const showUploadModal = ref(false);
const fileInput = ref(null);

const uploadForm = ref({
  category: 'financial',
  files: []
});

const categories = ref([
  { id: 'all', name: 'All Documents', icon: 'folder', count: 24 },
  { id: 'financial', name: 'Financial Reports', icon: 'account_balance', count: 12 },
  { id: 'market', name: 'Market Research', icon: 'trending_up', count: 8 },
  { id: 'legal', name: 'Legal Documents', icon: 'gavel', count: 3 },
  { id: 'other', name: 'Other', icon: 'description', count: 1 }
]);

const documents = ref([
  {
    id: 1,
    name: 'Tesla Q3 2024 10-K Filing',
    description: 'Annual financial report',
    type: 'pdf',
    size: '2.4 MB',
    uploadedAt: '2 days ago',
    status: 'processed',
    category: 'financial'
  },
  {
    id: 2,
    name: 'EV Market Analysis Report',
    description: 'Comprehensive market research',
    type: 'docx',
    size: '1.8 MB',
    uploadedAt: '5 days ago',
    status: 'processed',
    category: 'market'
  },
  {
    id: 3,
    name: 'Competitor Landscape Data',
    description: 'Market share and competitor analysis',
    type: 'xlsx',
    size: '890 KB',
    uploadedAt: '1 week ago',
    status: 'processed',
    category: 'market'
  },
  {
    id: 4,
    name: 'Investment Agreement Template',
    description: 'Standard investment terms',
    type: 'pdf',
    size: '420 KB',
    uploadedAt: '2 weeks ago',
    status: 'processed',
    category: 'legal'
  }
]);

const filteredDocuments = computed(() => {
  let filtered = documents.value;

  if (selectedCategory.value !== 'all') {
    filtered = filtered.filter(d => d.category === selectedCategory.value);
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(d =>
      d.name.toLowerCase().includes(query) ||
      d.description.toLowerCase().includes(query)
    );
  }

  return filtered;
});

const getFileIcon = (type) => {
  const icons = {
    pdf: 'picture_as_pdf',
    docx: 'description',
    xlsx: 'table_chart',
    csv: 'table_view',
    txt: 'article'
  };
  return icons[type] || 'description';
};

const triggerFileUpload = () => {
  fileInput.value.click();
};

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  uploadForm.value.files.push(...files);
};

const removeFile = (index) => {
  uploadForm.value.files.splice(index, 1);
};

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const uploadFiles = () => {
  console.log('Uploading files:', uploadForm.value);
  showUploadModal.value = false;
  uploadForm.value.files = [];
};
</script>
