<template>
  <div class="flex h-full gap-8 p-2">
    <!-- Left Sidebar: Categories -->
    <div class="w-72 flex-shrink-0 glass-panel rounded-2xl p-6 flex flex-col">
      <h3 class="text-xs font-bold text-text-secondary uppercase tracking-wider mb-6">{{ t('knowledge.newCategory') }}</h3>
      
      <div class="space-y-2 flex-1">
        <button
          v-for="category in categories"
          :key="category.id"
          @click="selectedCategory = category.id"
          :class="[
            'w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-300 text-left group',
            selectedCategory === category.id
              ? 'bg-primary/10 text-primary border border-primary/20 shadow-glow-sm'
              : 'text-text-secondary hover:bg-white/5 hover:text-white border border-transparent'
          ]"
        >
          <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-lg group-hover:scale-110 transition-transform">{{ category.icon }}</span>
            <span class="text-sm font-semibold">{{ category.name }}</span>
          </div>
          <span :class="[
              'text-xs px-2 py-0.5 rounded-md font-mono font-bold',
              selectedCategory === category.id ? 'bg-primary/20 text-primary' : 'bg-white/5 text-text-secondary'
          ]">
            {{ category.count }}
          </span>
        </button>
      </div>

      <div class="mt-6 pt-6 border-t border-white/10">
        <button class="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-text-primary transition-colors text-sm font-bold group">
          <span class="material-symbols-outlined group-hover:rotate-90 transition-transform">add</span>
          {{ t('knowledge.newCategory') }}
        </button>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden">
      <!-- Header -->
      <div class="p-8 border-b border-white/10 bg-white/5 backdrop-blur-md">
        <div class="flex items-center justify-between mb-6">
          <div>
            <h1 class="text-3xl font-display font-bold text-white mb-1 tracking-tight">{{ t('knowledge.title') }}</h1>
            <p class="text-sm text-text-secondary font-medium">
              {{ searchMode ? `${searchResults.length} search results` : `${filteredDocuments.length} ${t('knowledge.documentsCount')}` }}
            </p>
          </div>
          <div class="flex items-center gap-4">
            <div class="relative group">
              <div class="absolute inset-0 bg-primary/20 blur-md rounded-lg opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
              <input
                v-model="searchQuery"
                @keyup.enter="performSearch"
                type="text"
                :placeholder="t('knowledge.searchPlaceholder')"
                class="relative z-10 w-72 px-4 py-2.5 pl-10 pr-20 rounded-xl bg-black/20 border border-white/10 text-white placeholder-text-secondary focus:outline-none focus:border-primary/50 focus:bg-black/40 transition-all"
              />
              <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary z-20">
                search
              </span>
              <button
                v-if="searchMode"
                @click="clearSearch"
                class="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs rounded-md bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-colors font-bold z-20"
              >
                Clear
              </button>
              <button
                v-else-if="searchQuery"
                @click="performSearch"
                class="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-1 text-xs rounded-md bg-primary/20 text-primary hover:bg-primary/30 transition-colors font-bold z-20"
              >
                Search
              </button>
            </div>
            <button
              @click="showUploadModal = true"
              class="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white font-bold shadow-glow-sm hover:shadow-glow transition-all duration-300 hover:-translate-y-0.5"
            >
              <span class="material-symbols-outlined">cloud_upload</span>
              {{ t('knowledge.upload') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Documents List -->
      <div class="flex-1 overflow-hidden relative">
         <!-- Background Grid Pattern -->
         <div class="absolute inset-0 bg-tech-grid opacity-20 pointer-events-none"></div>

        <div class="overflow-y-auto h-full p-6">
          <table class="w-full border-separate border-spacing-y-2">
            <thead>
              <tr>
                <th class="text-left px-6 py-3 text-xs font-bold text-text-secondary uppercase tracking-wider">{{ t('knowledge.table.name') }}</th>
                <th class="text-left px-6 py-3 text-xs font-bold text-text-secondary uppercase tracking-wider">{{ t('knowledge.table.type') }}</th>
                <th class="text-left px-6 py-3 text-xs font-bold text-text-secondary uppercase tracking-wider">{{ t('knowledge.table.size') }}</th>
                <th class="text-left px-6 py-3 text-xs font-bold text-text-secondary uppercase tracking-wider">{{ t('knowledge.table.uploaded') }}</th>
                <th class="text-left px-6 py-3 text-xs font-bold text-text-secondary uppercase tracking-wider">{{ t('knowledge.table.status') }}</th>
                <th class="text-right px-6 py-3 text-xs font-bold text-text-secondary uppercase tracking-wider">{{ t('knowledge.table.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="doc in searchMode ? searchResults : filteredDocuments"
                :key="doc.id"
                class="group bg-white/5 hover:bg-white/10 transition-all duration-300"
              >
                <td class="px-6 py-4 rounded-l-xl border-y border-l border-white/5 group-hover:border-white/10">
                  <div class="flex items-center gap-4">
                    <div class="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0 text-primary group-hover:scale-110 transition-transform duration-300">
                      <span class="material-symbols-outlined">{{ getFileIcon(doc.metadata?.file_type) }}</span>
                    </div>
                    <div class="min-w-0">
                      <p class="font-bold text-white text-sm truncate max-w-[200px]">{{ doc.metadata?.title || doc.metadata?.filename || 'Untitled' }}</p>
                      <p class="text-xs text-text-secondary truncate max-w-[250px]">{{ doc.text ? doc.text.substring(0, 60) + '...' : 'No description' }}</p>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 border-y border-white/5 group-hover:border-white/10">
                  <span class="text-xs font-bold px-2.5 py-1 rounded-md bg-white/10 text-text-primary uppercase tracking-wide border border-white/10">
                    {{ doc.metadata?.file_type || 'UNK' }}
                  </span>
                </td>
                <td class="px-6 py-4 border-y border-white/5 group-hover:border-white/10 text-sm text-text-secondary font-mono">{{ formatFileSize(doc.text?.length) }}</td>
                <td class="px-6 py-4 border-y border-white/5 group-hover:border-white/10 text-sm text-text-secondary font-mono">{{ formatDate(doc.metadata?.created_at) }}</td>
                <td class="px-6 py-4 border-y border-white/5 group-hover:border-white/10">
                  <span v-if="searchMode && doc.score" class="text-xs px-2.5 py-1 rounded-full font-bold bg-primary/20 text-primary border border-primary/30">
                    {{ (doc.score * 100).toFixed(0) }}% Match
                  </span>
                  <span v-else class="text-xs px-2.5 py-1 rounded-full font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center w-fit gap-1">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> {{ t('knowledge.status.processed') }}
                  </span>
                </td>
                <td class="px-6 py-4 rounded-r-xl border-y border-r border-white/5 group-hover:border-white/10">
                  <div class="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button @click="confirmDelete(doc)" class="p-2 rounded-lg hover:bg-rose-500/20 text-text-secondary hover:text-rose-400 transition-colors" title="Delete">
                      <span class="material-symbols-outlined text-xl">delete</span>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Empty State -->
          <div v-if="filteredDocuments.length === 0" class="flex flex-col items-center justify-center h-96">
            <div class="w-24 h-24 rounded-full bg-white/5 flex items-center justify-center mb-6 animate-pulse">
               <span class="material-symbols-outlined text-6xl text-text-secondary/50">folder_open</span>
            </div>
            <h3 class="text-xl font-bold text-white mb-2">{{ t('knowledge.empty.title') }}</h3>
            <p class="text-text-secondary mb-8">{{ t('knowledge.empty.subtitle') }}</p>
            <button
              @click="showUploadModal = true"
              class="flex items-center gap-2 px-8 py-3 rounded-xl bg-primary/10 border border-primary/30 text-primary font-bold hover:bg-primary/20 transition-all hover:scale-105"
            >
              <span class="material-symbols-outlined">cloud_upload</span>
              {{ t('knowledge.empty.uploadButton') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Upload Modal -->
    <div
      v-if="showUploadModal"
      class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in"
      @click.self="showUploadModal = false"
    >
      <div class="glass-panel rounded-2xl p-8 max-w-lg w-full mx-4 border border-white/10 shadow-2xl">
        <div class="flex items-center justify-between mb-8 pb-4 border-b border-white/10">
          <h2 class="text-2xl font-bold text-white flex items-center gap-3">
             <span class="material-symbols-outlined text-primary">cloud_upload</span>
             {{ t('knowledge.uploadModal.title') }}
          </h2>
          <button
            @click="showUploadModal = false"
            class="p-2 rounded-lg hover:bg-white/10 text-text-secondary hover:text-white transition-colors"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="space-y-6">
          <!-- Title Input -->
          <div>
            <label class="block text-sm font-bold text-text-primary mb-2 uppercase tracking-wider">Title (Optional)</label>
            <input
              v-model="uploadForm.title"
              type="text"
              placeholder="Document title"
              class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white placeholder-text-secondary focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all"
            />
          </div>

          <!-- Category Selection -->
          <div>
            <label class="block text-sm font-bold text-text-primary mb-2 uppercase tracking-wider">{{ t('knowledge.uploadModal.category') }}</label>
            <div class="relative">
                <select
                v-model="uploadForm.category"
                class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all appearance-none cursor-pointer"
                >
                <option v-for="cat in categories.filter(c => c.id !== 'all')" :key="cat.id" :value="cat.id">
                    {{ cat.name }}
                </option>
                </select>
                <span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none">expand_more</span>
            </div>
          </div>

          <!-- File Upload -->
          <div>
            <label class="block text-sm font-bold text-text-primary mb-2 uppercase tracking-wider">{{ t('knowledge.uploadModal.files') }}</label>
            <div
              class="border-2 border-dashed border-white/10 rounded-xl p-10 text-center hover:border-primary/50 hover:bg-primary/5 transition-all cursor-pointer group"
              @click="triggerFileUpload"
            >
              <span class="material-symbols-outlined text-5xl text-text-secondary mb-4 group-hover:text-primary group-hover:scale-110 transition-all duration-300">cloud_upload</span>
              <p class="text-base text-white font-bold mb-2">
                {{ t('knowledge.uploadModal.uploadPrompt') }}
              </p>
              <p class="text-xs text-text-secondary font-medium">
                {{ t('knowledge.uploadModal.uploadHint') }}
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
            <div v-if="uploadForm.files.length > 0" class="mt-4 space-y-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
              <div
                v-for="(file, index) in uploadForm.files"
                :key="index"
                class="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5"
              >
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded bg-primary/20 flex items-center justify-center text-primary">
                     <span class="material-symbols-outlined text-lg">description</span>
                  </div>
                  <div>
                    <p class="text-sm font-bold text-white truncate max-w-[200px]">{{ file.name }}</p>
                    <p class="text-xs text-text-secondary font-mono">{{ formatFileSize(file.size) }}</p>
                  </div>
                </div>
                <button
                  @click="removeFile(index)"
                  class="text-text-secondary hover:text-rose-400 transition-colors"
                >
                  <span class="material-symbols-outlined">close</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-4 pt-6 border-t border-white/10">
            <button
              @click="showUploadModal = false"
              :disabled="uploading"
              class="flex-1 px-6 py-3 rounded-xl border border-white/10 text-text-primary hover:bg-white/5 transition-colors font-bold disabled:opacity-50"
            >
              {{ t('knowledge.uploadModal.cancel') }}
            </button>
            <button
              @click="uploadFiles"
              :disabled="uploadForm.files.length === 0 || uploading"
              :class="[
                'flex-1 px-6 py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2',
                uploadForm.files.length > 0 && !uploading
                  ? 'bg-gradient-to-r from-primary to-primary-dark text-white hover:shadow-glow'
                  : 'bg-white/5 text-text-secondary cursor-not-allowed border border-white/5'
              ]"
            >
              <span v-if="uploading" class="material-symbols-outlined animate-spin">progress_activity</span>
              <span v-else>{{ t('knowledge.uploadModal.upload') }} {{ uploadForm.files.length }} {{ t('knowledge.uploadModal.files') }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div
      v-if="showDeleteConfirm"
      class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in"
      @click.self="cancelDelete"
    >
      <div class="glass-panel border border-white/10 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
        <div class="flex flex-col items-center text-center mb-6">
          <div class="w-16 h-16 rounded-full bg-rose-500/20 flex items-center justify-center mb-4 shadow-[0_0_20px_rgba(244,63,94,0.3)]">
            <span class="material-symbols-outlined text-rose-500 text-3xl">delete_forever</span>
          </div>
          <h2 class="text-xl font-bold text-white mb-2">Delete Document?</h2>
          <p class="text-sm text-text-secondary leading-relaxed">
            Are you sure you want to delete "<strong>{{ documentToDelete?.metadata?.title || documentToDelete?.metadata?.filename }}</strong>"? This action cannot be undone.
          </p>
        </div>

        <div class="flex items-center gap-4">
          <button
            @click="cancelDelete"
            class="flex-1 px-6 py-3 rounded-xl border border-white/10 text-white hover:bg-white/10 transition-colors font-bold"
          >
            Cancel
          </button>
          <button
            @click="deleteDocument"
            class="flex-1 px-6 py-3 rounded-xl bg-gradient-to-r from-rose-500 to-rose-600 text-white hover:shadow-[0_0_15px_rgba(244,63,94,0.5)] transition-all font-bold"
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
import { useLanguage } from '../composables/useLanguage';
import { API_BASE } from '@/config/api';

const { success, error, warning } = useToast();
const { t } = useLanguage();

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
  { id: 'all', name: t('knowledge.categories.all'), icon: 'folder', count: 0 },
  { id: 'general', name: t('knowledge.categories.other'), icon: 'description', count: 0 },
  { id: 'financial', name: t('knowledge.categories.financial'), icon: 'account_balance', count: 0 },
  { id: 'market', name: t('knowledge.categories.market'), icon: 'trending_up', count: 0 },
  { id: 'legal', name: t('knowledge.categories.legal'), icon: 'gavel', count: 0 },
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
    txt: 'article',
    csv: 'table_chart',
    xlsx: 'table_view'
  };
  return icons[fileType?.toLowerCase()] || 'description';
};

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
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
    const response = await fetch(`${API_BASE}/api/knowledge/documents?limit=100`);
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
    const response = await fetch(`${API_BASE}/api/knowledge/stats`);
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

      const response = await fetch(`${API_BASE}/api/knowledge/upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }
    }

    success(`Successfully uploaded ${uploadForm.value.files.length} file(s)`);

    // Refresh BM25 index after upload
    try {
      await fetch(`${API_BASE}/api/knowledge/refresh-index`, {
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
      `${API_BASE}/api/knowledge/documents/${documentToDelete.value.id}`,
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
      `${API_BASE}/api/knowledge/hybrid-search?query=${encodeURIComponent(searchQuery.value)}&top_k=20&use_reranking=true${categoryParam}`
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