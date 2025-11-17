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
            {{ searchMode ? `${searchResults.length} search results` : `${filteredDocuments.length} documents` }}
          </p>
        </div>
        <div class="flex items-center gap-3">
          <div class="relative">
            <input
              v-model="searchQuery"
              @keyup.enter="performSearch"
              type="text"
              placeholder="Search documents..."
              class="w-64 px-4 py-2 pl-10 pr-20 rounded-lg bg-surface border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors"
            />
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">
              search
            </span>
            <button
              v-if="searchMode"
              @click="clearSearch"
              class="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs rounded bg-accent-red/20 text-accent-red hover:bg-accent-red/30 transition-colors"
            >
              Clear
            </button>
            <button
              v-else-if="searchQuery"
              @click="performSearch"
              class="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs rounded bg-primary/20 text-primary hover:bg-primary/30 transition-colors"
            >
              Search
            </button>
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
                v-for="doc in searchMode ? searchResults : filteredDocuments"
                :key="doc.id"
                class="border-t border-border-color hover:bg-background-dark transition-colors"
              >
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                      <span class="material-symbols-outlined text-primary">{{ getFileIcon(doc.metadata?.file_type) }}</span>
                    </div>
                    <div>
                      <p class="font-semibold text-text-primary text-sm">{{ doc.metadata?.title || doc.metadata?.filename || 'Untitled' }}</p>
                      <p class="text-xs text-text-secondary">{{ doc.text ? doc.text.substring(0, 60) + '...' : 'No description' }}</p>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span class="text-xs px-2 py-1 rounded bg-surface-light text-text-secondary uppercase">
                    {{ doc.metadata?.file_type || 'unknown' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-sm text-text-secondary">{{ formatFileSize(doc.text?.length) }}</td>
                <td class="px-6 py-4 text-sm text-text-secondary">{{ formatDate(doc.metadata?.created_at) }}</td>
                <td class="px-6 py-4">
                  <span v-if="searchMode && doc.score" class="text-xs px-2 py-1 rounded font-semibold bg-primary/20 text-primary">
                    {{ (doc.score * 100).toFixed(0) }}% match
                  </span>
                  <span v-else class="text-xs px-2 py-1 rounded font-semibold bg-accent-green/20 text-accent-green">
                    processed
                  </span>
                </td>
                <td class="px-6 py-4">
                  <div class="flex items-center justify-end gap-2">
                    <button @click="confirmDelete(doc)" class="p-2 rounded hover:bg-surface transition-colors" title="Delete">
                      <span class="material-symbols-outlined text-sm text-accent-red">delete</span>
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
          <!-- Title Input -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">Title (Optional)</label>
            <input
              v-model="uploadForm.title"
              type="text"
              placeholder="Document title"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors"
            />
          </div>

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
              :disabled="uploading"
              class="flex-1 px-4 py-3 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              @click="uploadFiles"
              :disabled="uploadForm.files.length === 0 || uploading"
              :class="[
                'flex-1 px-4 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2',
                uploadForm.files.length > 0 && !uploading
                  ? 'bg-primary text-background-dark hover:bg-primary/90'
                  : 'bg-surface text-text-secondary cursor-not-allowed'
              ]"
            >
              <span v-if="uploading" class="material-symbols-outlined animate-spin">progress_activity</span>
              <span v-else>Upload {{ uploadForm.files.length }} file{{ uploadForm.files.length !== 1 ? 's' : '' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div
      v-if="showDeleteConfirm"
      class="fixed inset-0 bg-background-dark/80 flex items-center justify-center z-50"
      @click.self="cancelDelete"
    >
      <div class="bg-surface border border-border-color rounded-lg p-6 max-w-md w-full mx-4">
        <div class="flex items-start gap-4 mb-6">
          <div class="w-12 h-12 rounded-lg bg-accent-red/20 flex items-center justify-center flex-shrink-0">
            <span class="material-symbols-outlined text-accent-red text-2xl">warning</span>
          </div>
          <div>
            <h2 class="text-xl font-bold text-text-primary mb-2">Delete Document</h2>
            <p class="text-sm text-text-secondary">
              Are you sure you want to delete "{{ documentToDelete?.metadata?.title || documentToDelete?.metadata?.filename }}"? This action cannot be undone.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <button
            @click="cancelDelete"
            class="flex-1 px-4 py-3 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors font-semibold"
          >
            Cancel
          </button>
          <button
            @click="deleteDocument"
            class="flex-1 px-4 py-3 rounded-lg bg-accent-red text-white hover:bg-accent-red/90 transition-colors font-semibold"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useToast } from '../composables/useToast';

const { success, error, warning } = useToast();

const selectedCategory = ref('all');
const searchQuery = ref('');
const showUploadModal = ref(false);
const showDeleteConfirm = ref(false);
const fileInput = ref(null);
const documentToDelete = ref(null);
const loading = ref(false);
const uploading = ref(false);
const searchMode = ref(false);
const searching = ref(false);
const searchResults = ref([]);

const uploadForm = ref({
  category: 'general',
  title: '',
  files: []
});

const categories = ref([
  { id: 'all', name: 'All Documents', icon: 'folder', count: 0 },
  { id: 'general', name: 'General', icon: 'description', count: 0 },
  { id: 'financial', name: 'Financial Reports', icon: 'account_balance', count: 0 },
  { id: 'market', name: 'Market Research', icon: 'trending_up', count: 0 },
  { id: 'legal', name: 'Legal Documents', icon: 'gavel', count: 0 },
  { id: 'technical', name: 'Technical Docs', icon: 'code', count: 0 }
]);

const documents = ref([]);
const stats = ref(null);

const filteredDocuments = computed(() => {
  let filtered = documents.value;

  if (selectedCategory.value !== 'all') {
    filtered = filtered.filter(d => d.metadata?.category === selectedCategory.value);
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(d =>
      d.metadata?.title?.toLowerCase().includes(query) ||
      d.metadata?.filename?.toLowerCase().includes(query) ||
      d.text?.toLowerCase().includes(query)
    );
  }

  return filtered;
});

const getFileIcon = (fileType) => {
  const icons = {
    pdf: 'picture_as_pdf',
    docx: 'description',
    doc: 'description',
    txt: 'article'
  };
  return icons[fileType] || 'description';
};

const formatFileSize = (bytes) => {
  if (!bytes) return 'Unknown';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const formatDate = (dateString) => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return date.toLocaleDateString();
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

const fetchDocuments = async () => {
  loading.value = true;
  try {
    const response = await fetch('http://localhost:8000/api/knowledge/documents?limit=100');
    if (!response.ok) throw new Error('Failed to fetch documents');

    const data = await response.json();
    documents.value = data.documents || [];

    // Update category counts
    updateCategoryCounts();
  } catch (err) {
    console.error('Error fetching documents:', err);
    error('Failed to load documents');
  } finally {
    loading.value = false;
  }
};

const fetchStats = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/knowledge/stats');
    if (!response.ok) throw new Error('Failed to fetch stats');

    stats.value = await response.json();
    categories.value[0].count = stats.value.total_documents || 0;
  } catch (err) {
    console.error('Error fetching stats:', err);
  }
};

const updateCategoryCounts = () => {
  const counts = {};
  documents.value.forEach(doc => {
    const category = doc.metadata?.category || 'general';
    counts[category] = (counts[category] || 0) + 1;
  });

  categories.value.forEach(cat => {
    if (cat.id === 'all') {
      cat.count = documents.value.length;
    } else {
      cat.count = counts[cat.id] || 0;
    }
  });
};

const uploadFiles = async () => {
  if (uploadForm.value.files.length === 0) return;

  uploading.value = true;

  try {
    for (const file of uploadForm.value.files) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('category', uploadForm.value.category);
      formData.append('title', uploadForm.value.title || file.name);

      const response = await fetch('http://localhost:8000/api/knowledge/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();
      console.log('Upload result:', result);
    }

    success(`Successfully uploaded ${uploadForm.value.files.length} file(s)`);

    // Refresh BM25 index after upload
    try {
      await fetch('http://localhost:8000/api/knowledge/refresh-index', {
        method: 'POST'
      });
    } catch (err) {
      console.warn('Failed to refresh index:', err);
    }

    // Reset form and reload documents
    uploadForm.value.files = [];
    uploadForm.value.title = '';
    showUploadModal.value = false;

    await fetchDocuments();
    await fetchStats();
  } catch (err) {
    console.error('Error uploading files:', err);
    error(err.message || 'Failed to upload files');
  } finally {
    uploading.value = false;
  }
};

const confirmDelete = (doc) => {
  documentToDelete.value = doc;
  showDeleteConfirm.value = true;
};

const cancelDelete = () => {
  documentToDelete.value = null;
  showDeleteConfirm.value = false;
};

const deleteDocument = async () => {
  if (!documentToDelete.value) return;

  try {
    const response = await fetch(
      `http://localhost:8000/api/knowledge/documents/${documentToDelete.value.id}`,
      { method: 'DELETE' }
    );

    if (!response.ok) throw new Error('Failed to delete document');

    success('Document deleted successfully');

    await fetchDocuments();
    await fetchStats();
  } catch (err) {
    console.error('Error deleting document:', err);
    error('Failed to delete document');
  } finally {
    cancelDelete();
  }
};

const performSearch = async () => {
  if (!searchQuery.value.trim()) {
    clearSearch();
    return;
  }

  searching.value = true;
  try {
    const categoryParam = selectedCategory.value !== 'all' ? `&category=${selectedCategory.value}` : '';
    const response = await fetch(
      `http://localhost:8000/api/knowledge/hybrid-search?query=${encodeURIComponent(searchQuery.value)}&top_k=20&use_reranking=true${categoryParam}`
    );

    if (!response.ok) throw new Error('Search failed');

    const data = await response.json();
    searchResults.value = data.results || [];
    searchMode.value = true;

    success(`Found ${searchResults.value.length} results`);
  } catch (err) {
    console.error('Error searching:', err);
    error('Search failed');
  } finally {
    searching.value = false;
  }
};

const clearSearch = () => {
  searchMode.value = false;
  searchQuery.value = '';
  searchResults.value = [];
};

onMounted(() => {
  fetchDocuments();
  fetchStats();
});
</script>
