import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Upload, FileText, Trash2, Eye, MessageSquare,
  Loader2, CloudUpload, Sparkles, ArrowUpRight, FileType
} from 'lucide-react';
import { uploadDocument, getDocuments, deleteDocument } from '../services/api';
import { StatusBadge, Skeleton, PageHeader, EmptyState } from '../components/ui';
import { useToast } from '../components/Toast';

const FILE_ICONS = {
  pdf: '📄', docx: '📝', txt: '📃',
};

export default function UploadPage() {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => { loadDocuments(); }, []);

  const loadDocuments = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.documents);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    for (const file of acceptedFiles) {
      setUploading(true);
      setUploadProgress(0);
      try {
        await uploadDocument(file, (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded / e.total) * 100));
        });
        toast.success('Upload Complete', `${file.name} uploaded successfully`);
        await loadDocuments();
        pollStatus();
      } catch (err) {
        toast.error('Upload Failed', err.response?.data?.detail || 'Something went wrong');
      } finally {
        setUploading(false);
        setUploadProgress(0);
      }
    }
  }, []);

  const pollStatus = () => {
    const interval = setInterval(async () => {
      try {
        const data = await getDocuments();
        setDocuments(data.documents);
        const allDone = data.documents.every(d => d.status === 'ready' || d.status === 'failed');
        if (allDone) {
          clearInterval(interval);
          toast.info('Processing Complete', 'All documents are ready');
        }
      } catch { clearInterval(interval); }
    }, 3000);
    setTimeout(() => clearInterval(interval), 120000);
  };

  const handleDelete = async (id, filename) => {
    if (!confirm(`Delete "${filename}"?`)) return;
    try {
      await deleteDocument(id);
      setDocuments(docs => docs.filter(d => d.id !== id));
      toast.success('Deleted', `${filename} removed`);
    } catch (err) {
      toast.error('Delete Failed', 'Could not delete document');
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxSize: 50 * 1024 * 1024,
    disabled: uploading,
  });

  return (
    <div className="space-y-8 animate-fade-in">
      <PageHeader title="Documents" subtitle="Upload, manage, and analyze your documents" />

      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`glass-card p-10 border-2 border-dashed cursor-pointer transition-all duration-300 group
          ${isDragActive ? 'border-primary-400 bg-primary-600/10 scale-[1.01]' : 'border-[var(--border-default)] hover:border-primary-500/50'}
          ${uploading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center text-center">
          {uploading ? (
            <>
              <div className="relative w-20 h-20 mb-4">
                <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
                  <circle cx="40" cy="40" r="35" fill="none" stroke="var(--bg-elevated)" strokeWidth="4" />
                  <circle cx="40" cy="40" r="35" fill="none" stroke="#6366f1" strokeWidth="4"
                    strokeDasharray={`${2 * Math.PI * 35}`}
                    strokeDashoffset={`${2 * Math.PI * 35 * (1 - uploadProgress / 100)}`}
                    strokeLinecap="round" className="transition-all duration-300" />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-primary-400">{uploadProgress}%</span>
              </div>
              <p className="text-lg font-medium text-[var(--text-primary)]">Uploading...</p>
              <p className="text-sm text-[var(--text-muted)] mt-1">Processing will start automatically</p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 rounded-2xl bg-primary-600/15 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                <CloudUpload className="w-8 h-8 text-primary-400" />
              </div>
              <p className="text-lg font-medium text-[var(--text-primary)]">
                {isDragActive ? 'Drop files here...' : 'Drag & drop documents or click to browse'}
              </p>
              <p className="text-sm text-[var(--text-muted)] mt-2">
                Supports <span className="text-primary-400 font-medium">PDF</span>, <span className="text-primary-400 font-medium">DOCX</span>, <span className="text-primary-400 font-medium">TXT</span> • Max 50MB
              </p>
            </>
          )}
        </div>
      </div>

      {/* Document List */}
      <div className="glass-card overflow-hidden animate-slide-up">
        <div className="p-5 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)]">
            Your Documents ({documents.length})
          </h3>
        </div>
        {loading ? (
          <div className="p-4 space-y-3">
            {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16" />)}
          </div>
        ) : documents.length > 0 ? (
          <div className="divide-y divide-[var(--border-subtle)]">
            {documents.map((doc, i) => (
              <div key={doc.id}
                className={`flex flex-col sm:flex-row sm:items-center justify-between p-4 hover:bg-[var(--bg-elevated)] transition-all animate-slide-up delay-${Math.min(i + 1, 5)} gap-3 sm:gap-0`}>
                <div className="flex items-start sm:items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary-500/15 to-purple-500/10 flex items-center justify-center text-lg border border-primary-500/10 shrink-0">
                    {FILE_ICONS[doc.file_type] || '📄'}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">{doc.original_filename}</p>
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3 mt-1">
                      <span className="text-xs text-[var(--text-muted)]">{(doc.file_size / 1024).toFixed(1)} KB</span>
                      <span className="text-xs text-[var(--text-muted)]">{doc.file_type.toUpperCase()}</span>
                      {doc.word_count > 0 && <span className="text-xs text-[var(--text-muted)]">{doc.word_count.toLocaleString()} words</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-between sm:justify-end gap-3 w-full sm:w-auto border-t sm:border-t-0 border-[var(--border-subtle)] pt-3 sm:pt-0 mt-1 sm:mt-0">
                  <StatusBadge status={doc.status} />
                  {doc.status === 'ready' && (
                    <div className="flex items-center gap-1 ml-2">
                      <Link to={`/documents/${doc.id}`}
                        className="p-2 rounded-lg hover:bg-primary-600/15 text-[var(--text-muted)] hover:text-primary-400 transition-colors" title="View">
                        <Eye className="w-4 h-4" />
                      </Link>
                      <Link to={`/documents/${doc.id}/chat`}
                        className="p-2 rounded-lg hover:bg-green-600/15 text-[var(--text-muted)] hover:text-green-400 transition-colors" title="Chat">
                        <MessageSquare className="w-4 h-4" />
                      </Link>
                      <Link to={`/documents/${doc.id}`}
                        className="p-2 rounded-lg hover:bg-purple-600/15 text-[var(--text-muted)] hover:text-purple-400 transition-colors" title="Insights">
                        <Sparkles className="w-4 h-4" />
                      </Link>
                    </div>
                  )}
                  <button onClick={() => handleDelete(doc.id, doc.original_filename)}
                    className="p-2 rounded-lg hover:bg-red-600/15 text-[var(--text-muted)] hover:text-red-400 transition-colors" title="Delete">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon={FileText} title="No documents uploaded"
            description="Upload your first document to unlock AI-powered analysis, search, and chat" />
        )}
      </div>
    </div>
  );
}
