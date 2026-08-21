import React, { useState, useEffect } from 'react';
import { api } from '../services/api.js';
import { useStore } from '../store/useStore.js';
import {
  ShieldCheck, FileText, Table, Box, Download,
  Trash2, CheckCircle2, AlertTriangle, AlertCircle, Lock
} from 'lucide-react';

export const PrivacyPage = () => {
  const [downloadingFormat, setDownloadingFormat] = useState(null);
  const [exportError, setExportError] = useState('');
  const [exportSuccess, setExportSuccess] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [consents, setConsents] = useState([]);
  const { logout } = useStore();

  useEffect(() => {
    const loadConsents = async () => {
      try {
        const records = await api.getConsents();
        if (Array.isArray(records) && records.length > 0) {
          setConsents(records);
        }
      } catch (e) {
        console.warn("Unable to load consent records:", e);
      }
    };
    loadConsents();
  }, []);

  const handleDownload = async (format) => {
    if (downloadingFormat) return;
    setDownloadingFormat(format);
    setExportError('');
    setExportSuccess('');

    try {
      const res = await api.downloadExport(format);
      setExportSuccess(`Successfully exported your ${format.toUpperCase()} archive.`);
      setTimeout(() => setExportSuccess(''), 5000);
    } catch (e) {
      setExportError(e.message || "Unable to export data at this moment.");
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleDeleteAccount = async () => {
    if (!window.confirm("Are you sure you want to permanently delete your NutriQ account and all meal records? This cannot be undone.")) {
      return;
    }
    setDeleting(true);
    try {
      await api.deleteAccount();
      alert("Account permanently deleted.");
      logout();
    } catch (e) {
      alert("Failed to delete account.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: '1200px' }}>
      
      {/* Header */}
      <div className="wellness-card" style={{ padding: '24px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '42px', height: '42px', borderRadius: '12px',
            background: 'var(--primary-gradient)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(31, 122, 90, 0.25)'
          }}>
            <ShieldCheck size={22} color="#FFFFFF" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: '800', margin: 0, color: 'var(--text-primary)' }}>
              Privacy & Data Protection
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', margin: 0 }}>
              Manage your personal information, download meal archives, and control active AI processing consents.
            </p>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {exportSuccess && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 16px',
          background: 'var(--primary-light)', border: '1px solid rgba(31, 122, 90, 0.3)',
          borderRadius: 'var(--radius-md)', color: 'var(--primary-dark)', fontSize: '0.86rem', fontWeight: '700'
        }}>
          <CheckCircle2 size={18} /> {exportSuccess}
        </div>
      )}

      {exportError && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '10px', padding: '12px 16px',
          background: 'var(--error-bg)', border: '1px solid rgba(217, 93, 93, 0.3)',
          borderRadius: 'var(--radius-md)', color: 'var(--error-rose)', fontSize: '0.86rem', fontWeight: '700'
        }}>
          <AlertCircle size={18} /> {exportError}
        </div>
      )}

      {/* Data Export Options */}
      <div className="wellness-card" style={{ padding: '28px' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: '800', margin: '0 0 16px 0', color: 'var(--text-primary)' }}>
          Data Portability & Export
        </h3>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Download a complete export of your personal profile, nutrition goals, meal journal history, and water logs at any time.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          
          <div style={{ background: 'var(--bg-subtle)', padding: '18px', borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
            <div>
              <h4 style={{ fontSize: '1.02rem', fontWeight: '800', margin: '0 0 4px 0', color: 'var(--text-primary)' }}>PDF Clinical Report</h4>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0 }}>Formatted summary suitable for sharing with nutritionists.</p>
            </div>
            <button
              type="button"
              onClick={() => handleDownload('pdf')}
              disabled={Boolean(downloadingFormat)}
              className="btn-primary"
              style={{ width: '100%', padding: '10px 16px', fontSize: '0.86rem', fontWeight: '700' }}
            >
              <Download size={15} /> {downloadingFormat === 'pdf' ? 'Generating PDF...' : 'Download PDF'}
            </button>
          </div>

          <div style={{ background: 'var(--bg-subtle)', padding: '18px', borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
            <div>
              <h4 style={{ fontSize: '1.02rem', fontWeight: '800', margin: '0 0 4px 0', color: 'var(--text-primary)' }}>CSV Spreadsheet</h4>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0 }}>Structured tabular data compatible with Excel and Google Sheets.</p>
            </div>
            <button
              type="button"
              onClick={() => handleDownload('csv')}
              disabled={Boolean(downloadingFormat)}
              className="btn-primary"
              style={{ width: '100%', padding: '10px 16px', fontSize: '0.86rem', fontWeight: '700' }}
            >
              <Download size={15} /> {downloadingFormat === 'csv' ? 'Generating CSV...' : 'Download CSV'}
            </button>
          </div>

          <div style={{ background: 'var(--bg-subtle)', padding: '18px', borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
            <div>
              <h4 style={{ fontSize: '1.02rem', fontWeight: '800', margin: '0 0 4px 0', color: 'var(--text-primary)' }}>JSON Raw Export</h4>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0 }}>Complete raw machine-readable JSON archive of all database records.</p>
            </div>
            <button
              type="button"
              onClick={() => handleDownload('json')}
              disabled={Boolean(downloadingFormat)}
              className="btn-primary"
              style={{ width: '100%', padding: '10px 16px', fontSize: '0.86rem', fontWeight: '700' }}
            >
              <Download size={15} /> {downloadingFormat === 'json' ? 'Generating JSON...' : 'Download JSON'}
            </button>
          </div>

        </div>
      </div>

      {/* Danger Zone: Account Deletion */}
      <div className="wellness-card" style={{ padding: '28px', border: '1px solid rgba(217, 93, 93, 0.3)', background: 'var(--error-bg)' }}>
        <h3 style={{ fontSize: '1.15rem', fontWeight: '800', margin: '0 0 8px 0', color: 'var(--error-rose)' }}>
          Permanent Account Deletion
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Deleting your account will permanently remove all your biometric profiles, meal history logs, and goal progress.
        </p>
        <button
          type="button"
          onClick={handleDeleteAccount}
          disabled={deleting}
          className="btn-secondary"
          style={{ color: 'var(--error-rose)', borderColor: 'var(--error-rose)', padding: '9px 18px', fontSize: '0.84rem' }}
        >
          <Trash2 size={15} /> Delete NutriQ Account
        </button>
      </div>

    </div>
  );
};
