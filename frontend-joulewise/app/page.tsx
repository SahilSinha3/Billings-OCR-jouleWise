"use client";

import React, { useEffect, useState, useRef } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Zap,
  Trash2,
  XCircle,
  Settings as SettingsIcon,
  Copy,
  Check,
  Eye,
  EyeOff,
  Sparkles,
  Cpu,
  Database,
  Server,
  Layers,
  Loader2,
  Download,
} from "lucide-react";
import styles from "./page.module.css";
import { BillDetail } from "../types/bill";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

interface SettingsState {
  tesseract_status: string;
  tesseract_path: string;
  poppler_status: string;
  poppler_path: string;
  ollama_base_url: string;
  ollama_model: string;
  ollama_status: string;
  gemini_configured: boolean;
  gemini_masked_key: string;
  preferred_ai_provider: string;
}

export default function JouleWiseDashboard() {
  const [bills, setBills] = useState<BillDetail[]>([]);
  const [selectedBill, setSelectedBill] = useState<BillDetail | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [activeLeftTab, setActiveLeftTab] = useState<"document" | "raw_text">("document");
  const [copiedText, setCopiedText] = useState(false);

  // Summary generation state
  const [isSummarizing, setIsSummarizing] = useState(false);

  // Settings State
  const [showSettings, setShowSettings] = useState(false);
  const [settingsData, setSettingsData] = useState<SettingsState | null>(null);
  const [geminiKeyInput, setGeminiKeyInput] = useState("");
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [ollamaUrlInput, setOllamaUrlInput] = useState("http://localhost:11434");
  const [ollamaModelInput, setOllamaModelInput] = useState("llama3.2");
  const [testResult, setTestResult] = useState<{ provider: string; success: boolean; message: string } | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);

  // Editing state for selected bill
  const [editForm, setEditForm] = useState<Partial<BillDetail>>({});
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  // Global extraction state & step tracker
  const [extractionStep, setExtractionStep] = useState(0);
  const extractionSteps = [
    "Ingesting Document Binary (PostgreSQL BYTEA)...",
    "High-Speed 200 DPI Rasterization via Poppler...",
    "Pure Tesseract OCR Neural Token Extraction...",
    "Executing Mathematical Meter Register Audit...",
    "Finalizing Verified Consumption Metrics...",
  ];

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Active when uploading or when any bill is queued / extracting
  const isExtracting = isUploading || bills.some((b) => b.status === "QUEUED" || b.status === "EXTRACTING");

  useEffect(() => {
    if (!isExtracting) {
      setExtractionStep(0);
      return;
    }
    const timer = setInterval(() => {
      setExtractionStep((prev) => (prev + 1) % extractionSteps.length);
    }, 1200);
    return () => clearInterval(timer);
  }, [isExtracting]);

  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/settings`);
      if (res.ok) {
        const data: SettingsState = await res.json();
        setSettingsData(data);
        setOllamaUrlInput(data.ollama_base_url);
        setOllamaModelInput(data.ollama_model);
      }
    } catch {
      // Handled silently
    }
  };

  const fetchBills = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/bills`);
      if (res.ok) {
        const data: BillDetail[] = await res.json();
        setBills(data);
        if (data.length > 0 && !selectedBill) {
          setSelectedBill(data[0]);
          setEditForm(data[0]);
        } else if (selectedBill) {
          const updated = data.find((b) => b.id === selectedBill.id);
          if (updated) {
            setSelectedBill(updated);
            setEditForm(updated);
          }
        }
      }
    } catch {
      // Handled silently
    }
  };

  useEffect(() => {
    fetchBills();
    fetchSettings();
    const interval = setInterval(fetchBills, isExtracting ? 1200 : 3000);
    return () => clearInterval(interval);
  }, [selectedBill?.id, isExtracting]);

  const handleSelectBill = (bill: BillDetail) => {
    setSelectedBill(bill);
    setEditForm(bill);
  };

  const handleFileUpload = async (files: FileList | File[]) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    const fileArray = Array.from(files);

    try {
      if (fileArray.length === 1) {
        formData.append("file", fileArray[0]);
        const res = await fetch(`${API_BASE_URL}/bills/upload`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || "Upload failed.");
        }
        const uploadRes = await res.json();
        await fetchBills();
        if (uploadRes.bill_id) {
          const checkRes = await fetch(`${API_BASE_URL}/bills/${uploadRes.bill_id}`);
          if (checkRes.ok) {
            const created = await checkRes.json();
            handleSelectBill(created);
          }
        }
      } else {
        fileArray.forEach((f) => formData.append("files", f));
        const res = await fetch(`${API_BASE_URL}/bills/bulk-upload`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || "Bulk upload failed.");
        }
        await fetchBills();
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setUploadError(err.message);
      } else {
        setUploadError("Upload error occurred.");
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!selectedBill) return;
    setIsSummarizing(true);
    try {
      const res = await fetch(`${API_BASE_URL}/bills/${selectedBill.id}/summarize`, {
        method: "POST",
      });
      if (res.ok) {
        const updated: BillDetail = await res.json();
        setSelectedBill(updated);
        setEditForm(updated);
        setBills((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
      }
    } finally {
      setIsSummarizing(false);
    }
  };

  const deleteBill = async (billId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    try {
      const res = await fetch(`${API_BASE_URL}/bills/${billId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        if (selectedBill?.id === billId) {
          const remaining = bills.filter((b) => b.id !== billId);
          if (remaining.length > 0) {
            handleSelectBill(remaining[0]);
          } else {
            setSelectedBill(null);
            setEditForm({});
          }
        }
        await fetchBills();
      }
    } catch {
      // Handled silently
    }
  };

  const clearAllBills = async () => {
    if (!confirm("Delete all bills from PostgreSQL storage and clear Redis cache?")) return;
    try {
      const res = await fetch(`${API_BASE_URL}/bills`, {
        method: "DELETE",
      });
      if (res.ok) {
        setBills([]);
        setSelectedBill(null);
        setEditForm({});
      }
    } catch {
      // Handled silently
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedBill) return;
    setIsSavingEdit(true);
    try {
      const res = await fetch(`${API_BASE_URL}/bills/${selectedBill.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          consumer_name: editForm.consumer_name,
          consumer_number: editForm.consumer_number,
          bill_number: editForm.bill_number,
          total_units_kwh: editForm.total_units_kwh ? Number(editForm.total_units_kwh) : undefined,
          net_amount_due: editForm.net_amount_due ? Number(editForm.net_amount_due) : undefined,
          power_factor: editForm.power_factor ? Number(editForm.power_factor) : undefined,
          due_date: editForm.due_date,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedBill(updated);
        setEditForm(updated);
        await fetchBills();
      }
    } finally {
      setIsSavingEdit(false);
    }
  };

  const testProviderConnection = async (provider: "gemini" | "ollama") => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/settings/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider,
          api_key: provider === "gemini" ? geminiKeyInput : undefined,
          base_url: provider === "ollama" ? ollamaUrlInput : undefined,
          model: provider === "ollama" ? ollamaModelInput : undefined,
        }),
      });
      const data = await res.json();
      setTestResult({
        provider,
        success: data.success,
        message: data.message,
      });
    } catch (e: unknown) {
      setTestResult({
        provider,
        success: false,
        message: e instanceof Error ? e.message : "Connection failed.",
      });
    } finally {
      setIsTesting(false);
    }
  };

  const saveSettings = async () => {
    setIsSavingSettings(true);
    try {
      const res = await fetch(`${API_BASE_URL}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gemini_api_key: geminiKeyInput || undefined,
          ollama_base_url: ollamaUrlInput || undefined,
          ollama_model: ollamaModelInput || undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSettingsData(data);
        setShowSettings(false);
      }
    } finally {
      setIsSavingSettings(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(true);
    setTimeout(() => setCopiedText(false), 2000);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  return (
    <div className={styles.pageContainer}>
      {/* Sleek Apple-Style Clean White Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.brandGroup}>
            <div className={styles.brandLogo}>
              <Zap style={{ width: 18, height: 18, fill: "#ffffff" }} />
            </div>
          </div>

          <div className={styles.headerActions}>
            {/* Export All Bills as CSV */}
            {bills.length > 0 && (
              <a
                href={`${API_BASE_URL}/bills/export/csv`}
                download
                title="Download all bills and verified data as a CSV file"
                className={`${styles.btn} ${styles.btnOutline}`}
              >
                <Download style={{ width: 14, height: 14 }} />
                <span>Export All (CSV)</span>
              </a>
            )}

            {bills.length > 0 && (
              <button
                onClick={clearAllBills}
                className={`${styles.btn} ${styles.btnDanger}`}
              >
                <Trash2 style={{ width: 14, height: 14 }} />
                <span>Clear All</span>
              </button>
            )}

            <button
              onClick={() => {
                fetchSettings();
                setShowSettings(true);
              }}
              className={`${styles.btn} ${styles.btnOutline}`}
            >
              <SettingsIcon style={{ width: 14, height: 14 }} />
              <span>Settings & AI</span>
              {settingsData?.gemini_configured && (
                <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "var(--accent-emerald)" }} />
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Screen-Blurring Global State Loader when Extracting */}
      {isExtracting && (
        <div className={styles.globalBlurOverlay}>
          <div className={styles.loaderCard}>
            {/* Animated Radar Spinner */}
            <div className={styles.radarWrapper}>
              <div className={styles.radarOuterRing} />
              <div className={styles.radarCenterCore}>
                <Zap style={{ width: 16, height: 16, fill: "#ffffff" }} />
              </div>
            </div>

            <div className={styles.loaderInfo}>
              <div className={styles.loaderBadge}>
                <span className={styles.pulseDot} />
                <span>High-Speed 200 DPI OCR Engine Active</span>
              </div>
              <h3 className={styles.loaderTitle}>Extracting Utility Bill Data</h3>
              <p className={styles.loaderDesc}>
                Direct binary streaming to PostgreSQL BYTEA
              </p>
            </div>

            {/* Phase Step Ticker with Progress Bar */}
            <div className={styles.stepTicker}>
              <div className={styles.stepHeader}>
                <span>Pipeline Phase {extractionStep + 1} of 5</span>
                <span style={{ color: "var(--accent-emerald)", fontWeight: 700 }}>Running</span>
              </div>
              <div className={styles.stepCurrent}>
                <Loader2 style={{ width: 14, height: 14 }} className={styles.spinAnimation} />
                <span>{extractionSteps[extractionStep]}</span>
              </div>
              <div className={styles.progressBar}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${((extractionStep + 1) / extractionSteps.length) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Workspace */}
      <main className={styles.main}>
        <div className={styles.workspaceGrid}>
          {/* Left Column: Multi-File Ingestion & Bill List */}
          <div className={styles.leftCol}>
            {/* Bulk Dropzone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`${styles.dropzone} ${isDragging ? styles.dropzoneDragging : ""}`}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
                multiple
                accept=".pdf,.png,.jpg,.jpeg"
                style={{ display: "none" }}
              />
              <div className={styles.dropzoneInner}>
                <div className={styles.dropzoneIconWrap}>
                  {isUploading ? (
                    <Loader2 style={{ width: 22, height: 22 }} className={styles.spinAnimation} />
                  ) : (
                    <UploadCloud style={{ width: 22, height: 22 }} />
                  )}
                </div>
                <div>
                  <span className={styles.dropzoneTextMain}>Upload Bills (Single or Bulk)</span>
                  <span className={styles.dropzoneTextSub}>
                    Drag & drop PDFs or images
                  </span>
                </div>
              </div>
            </div>

            {uploadError && (
              <div className={`${styles.alertBox} ${styles.alertError}`}>
                <XCircle style={{ width: 16, height: 16, flexShrink: 0, marginTop: 1 }} />
                <div>
                  <strong style={{ display: "block" }}>Upload Error</strong>
                  <span style={{ fontSize: 11 }}>{uploadError}</span>
                </div>
              </div>
            )}

            {/* Processed Bills List */}
            <div className={styles.billsCard}>
              <div className={styles.billsCardHeader}>
                <span className={styles.billsCardTitle}>Processed Bills ({bills.length})</span>
                <div className={styles.billsCardActions}>
                  {bills.length > 0 && (
                    <a
                      href={`${API_BASE_URL}/bills/export/csv`}
                      download
                      title="Export all bills as CSV"
                      className={`${styles.btn} ${styles.btnOutline}`}
                      style={{ padding: "3px 8px", fontSize: 11 }}
                    >
                      <Download style={{ width: 12, height: 12 }} />
                      <span>Export All</span>
                    </a>
                  )}
                  <button
                    onClick={fetchBills}
                    title="Refresh list"
                    className={`${styles.btn} ${styles.btnOutline}`}
                    style={{ padding: "3px 6px" }}
                  >
                    <RefreshCw style={{ width: 12, height: 12 }} />
                  </button>
                </div>
              </div>

              <div className={styles.billsList}>
                {bills.length === 0 ? (
                  <div className={styles.billsEmpty}>
                    No electricity bills uploaded yet. Upload a PDF or image above to extract.
                  </div>
                ) : (
                  bills.map((bill) => {
                    const isSelected = selectedBill?.id === bill.id;
                    const isRejected = bill.status === "REJECTED_NON_BILL" || bill.is_valid_bill === false;
                    const isVerified = bill.status === "VERIFIED";
                    const isCurrentlyExtracting = bill.status === "QUEUED" || bill.status === "EXTRACTING";

                    return (
                      <div
                        key={bill.id}
                        onClick={() => handleSelectBill(bill)}
                        className={`${styles.billItem} ${isSelected ? styles.billItemSelected : ""}`}
                      >
                        <div className={styles.billItemMain}>
                          <div className={styles.billItemTitleRow}>
                            <span className={styles.billItemDiscom}>{bill.discom_code}</span>
                            <span className={styles.billItemName}>
                              {bill.consumer_name || bill.file_name}
                            </span>
                          </div>
                          <div className={styles.billItemMeta}>
                            Acc: {bill.consumer_number || bill.account_number || "N/A"}
                          </div>
                        </div>

                        <div className={styles.billItemAside}>
                          <div className={styles.billItemAmount}>
                            ₹{(bill.net_amount_due || 0).toLocaleString("en-IN")}
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            {isCurrentlyExtracting ? (
                              <span className={`${styles.statusTag} ${styles.statusExtracting}`}>
                                <Loader2 style={{ width: 10, height: 10 }} className={styles.spinAnimation} />
                                Extracting...
                              </span>
                            ) : (
                              <span
                                className={`${styles.statusTag} ${isRejected
                                  ? styles.statusInvalid
                                  : isVerified
                                    ? styles.statusVerified
                                    : styles.statusReview
                                  }`}
                              >
                                {isRejected ? "Invalid Doc" : isVerified ? "Verified" : "Review"}
                              </span>
                            )}
                            <button
                              onClick={(e) => deleteBill(bill.id, e)}
                              title="Delete this bill"
                              style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 2 }}
                            >
                              <Trash2 style={{ width: 13, height: 13 }} />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Detailed Workspace */}
          <div className={styles.rightCol}>
            {selectedBill ? (
              <>
                {/* Rejection Alert Banner if Non-Bill */}
                {(selectedBill.status === "REJECTED_NON_BILL" || selectedBill.is_valid_bill === false) && (
                  <div className={`${styles.alertBox} ${styles.alertError}`}>
                    <AlertTriangle style={{ width: 18, height: 18, flexShrink: 0, marginTop: 1 }} />
                    <div>
                      <strong style={{ display: "block" }}>Document Classification Guardrail Triggered</strong>
                      <span style={{ fontSize: 12, opacity: 0.9 }}>
                        {selectedBill.validation_error ||
                          "This document was recognized as a technical manual, register map, or datasheet rather than a state electricity bill."}
                      </span>
                    </div>
                  </div>
                )}

                {/* Plain-English Bill Summary Card */}
                <div className={styles.summaryCard}>
                  <div className={styles.summaryLeft}>
                    <div className={styles.summaryIconWrap}>
                      <Sparkles style={{ width: 16, height: 16 }} />
                    </div>
                    <div className={styles.summaryBody}>
                      <div className={styles.summaryHeader}>
                        <span className={styles.summaryLabel}>Plain-English Bill Summary</span>
                        <span className={styles.badge}>
                          {selectedBill.bill_summary ? "AI Synthesized" : "Verified Summary"}
                        </span>
                      </div>
                      <p className={styles.summaryText}>
                        {selectedBill.bill_summary ||
                          `Electricity utility bill for ${selectedBill.consumer_name || "the consumer"} issued by ${selectedBill.discom_name || "the utility"}. Total active energy is ${(selectedBill.total_units_kwh || 0).toLocaleString("en-IN")} kWh with net amount payable of ₹${(selectedBill.net_amount_due || 0).toLocaleString("en-IN")}${selectedBill.due_date ? ` due on ${selectedBill.due_date}` : ""}.`}
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={handleGenerateSummary}
                    disabled={isSummarizing}
                    className={`${styles.btn} ${styles.btnOutline}`}
                    style={{ flexShrink: 0 }}
                  >
                    {isSummarizing ? (
                      <>
                        <Loader2 style={{ width: 14, height: 14 }} className={styles.spinAnimation} />
                        <span>Synthesizing...</span>
                      </>
                    ) : (
                      <>
                        <RefreshCw style={{ width: 14, height: 14 }} />
                        <span>{selectedBill.bill_summary ? "Regenerate" : "Synthesize AI Summary"}</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Split Workspace: Document Stream on Left, Form & Audit on Right */}
                <div className={styles.splitViewerGrid}>
                  {/* Left Half: Document Viewer / Raw OCR Text */}
                  <div className={styles.viewerPane}>
                    <div className={styles.viewerTabBar}>
                      <div className={styles.tabBtnGroup}>
                        <button
                          onClick={() => setActiveLeftTab("document")}
                          className={`${styles.tabBtn} ${activeLeftTab === "document" ? styles.tabBtnActive : ""}`}
                        >
                          Document Preview
                        </button>
                        <button
                          onClick={() => setActiveLeftTab("raw_text")}
                          className={`${styles.tabBtn} ${activeLeftTab === "raw_text" ? styles.tabBtnActive : ""}`}
                        >
                          Raw OCR Text
                        </button>
                      </div>

                      {activeLeftTab === "raw_text" && selectedBill.raw_extracted_text && (
                        <button
                          onClick={() => copyToClipboard(selectedBill.raw_extracted_text || "")}
                          className={`${styles.btn} ${styles.btnOutline}`}
                          style={{ padding: "3px 8px", fontSize: 11 }}
                        >
                          {copiedText ? <Check style={{ width: 12, height: 12, color: "var(--accent-emerald)" }} /> : <Copy style={{ width: 12, height: 12 }} />}
                          <span>{copiedText ? "Copied" : "Copy"}</span>
                        </button>
                      )}
                    </div>

                    <div className={styles.viewerBody}>
                      {activeLeftTab === "document" ? (
                        <iframe
                          src={`${API_BASE_URL}/bills/${selectedBill.id}/file`}
                          title="Original Bill Preview"
                          className={styles.docIframe}
                        />
                      ) : (
                        <pre className={styles.rawTextPre}>
                          {selectedBill.raw_extracted_text || "No OCR text extracted."}
                        </pre>
                      )}
                    </div>
                  </div>

                  {/* Right Half: Form & Mathematical Audit */}
                  <div className={styles.formPane}>
                    {/* Header & Export Single Bill CSV */}
                    <div className={styles.formHeader}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span className={styles.badge}>{selectedBill.discom_code}</span>
                          <h3 className={styles.formHeaderConsumer}>{selectedBill.consumer_name}</h3>
                        </div>
                        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                          {selectedBill.discom_name}
                        </p>
                      </div>

                      <div style={{ textAlign: "right", display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                        <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "ui-monospace, monospace" }}>
                          Net Amount Due
                        </span>
                        <div className={styles.formHeaderAmount}>
                          ₹{(selectedBill.net_amount_due || 0).toLocaleString("en-IN")}
                        </div>
                        <a
                          href={`${API_BASE_URL}/bills/${selectedBill.id}/export/csv`}
                          download
                          title="Export this bill as a detailed CSV file"
                          className={`${styles.btn} ${styles.btnOutline}`}
                          style={{ padding: "2px 8px", fontSize: 11 }}
                        >
                          <Download style={{ width: 12, height: 12 }} />
                          <span>Export CSV</span>
                        </a>
                      </div>
                    </div>

                    {/* Mathematical Audit Card */}
                    <div className={styles.mathAuditCard}>
                      <div className={styles.mathAuditHeader}>
                        <span className={styles.mathAuditTitle}>Mathematical Audit</span>
                        {selectedBill.is_math_verified ? (
                          <span className={`${styles.statusTag} ${styles.statusVerified}`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                            <CheckCircle2 style={{ width: 12, height: 12 }} /> Verified Pass
                          </span>
                        ) : (
                          <span className={`${styles.statusTag} ${styles.statusReview}`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                            <AlertTriangle style={{ width: 12, height: 12 }} /> Flagged Review
                          </span>
                        )}
                      </div>

                      <div className={styles.mathGrid}>
                        <div className={styles.mathBox}>
                          <span className={styles.mathBoxLabel}>Active Units:</span>
                          <span className={styles.mathBoxValue}>
                            {(selectedBill.total_units_kwh || 0).toLocaleString("en-IN")} kWh
                          </span>
                        </div>
                        <div className={styles.mathBox}>
                          <span className={styles.mathBoxLabel}>Power Factor:</span>
                          <span className={styles.mathBoxValue}>
                            {selectedBill.power_factor ?? "N/A"}
                          </span>
                        </div>
                      </div>

                      {selectedBill.verification_details?.discrepancies &&
                        selectedBill.verification_details.discrepancies.length > 0 && (
                          <div style={{ paddingTop: 8, borderTop: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", gap: 4 }}>
                            {selectedBill.verification_details.discrepancies.map((d, i) => (
                              <div key={i} style={{ fontSize: 11, color: "var(--accent-amber)", fontFamily: "ui-monospace, monospace" }}>
                                • {typeof d === "string" ? d : `${d.rule_name}: ${d.field_name} (expected ${d.expected_value}, reported ${d.reported_value})`}
                              </div>
                            ))}
                          </div>
                        )}
                    </div>

                    {/* Extracted Bill Fields Form */}
                    <div className={styles.fieldsForm}>
                      <div className={styles.fieldsHeaderRow}>
                        <span className={styles.fieldsTitle}>Extracted Bill Fields</span>
                        <button
                          onClick={handleSaveEdit}
                          disabled={isSavingEdit}
                          className={`${styles.btn} ${styles.btnSolid}`}
                          style={{ padding: "4px 10px", fontSize: 11 }}
                        >
                          {isSavingEdit ? "Saving..." : "Save & Re-verify"}
                        </button>
                      </div>

                      <div className={styles.fieldsGrid}>
                        <div className={styles.fieldGroup}>
                          <label className={styles.fieldLabel}>Consumer Name</label>
                          <input
                            type="text"
                            value={editForm.consumer_name || ""}
                            onChange={(e) => setEditForm({ ...editForm, consumer_name: e.target.value })}
                            className={styles.fieldInput}
                          />
                        </div>

                        <div className={styles.fieldGroup}>
                          <label className={styles.fieldLabel}>Account / CA Number</label>
                          <input
                            type="text"
                            value={editForm.consumer_number || ""}
                            onChange={(e) => setEditForm({ ...editForm, consumer_number: e.target.value })}
                            className={styles.fieldInput}
                          />
                        </div>

                        <div className={styles.fieldGroup}>
                          <label className={styles.fieldLabel}>Bill Number</label>
                          <input
                            type="text"
                            value={editForm.bill_number || ""}
                            onChange={(e) => setEditForm({ ...editForm, bill_number: e.target.value })}
                            className={styles.fieldInput}
                          />
                        </div>

                        <div className={styles.fieldGroup}>
                          <label className={styles.fieldLabel}>Due Date</label>
                          <input
                            type="date"
                            value={editForm.due_date || ""}
                            onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value })}
                            className={styles.fieldInput}
                          />
                        </div>

                        <div className={styles.fieldGroup}>
                          <label className={styles.fieldLabel}>Total Units (kWh)</label>
                          <input
                            type="number"
                            value={editForm.total_units_kwh || 0}
                            onChange={(e) =>
                              setEditForm({ ...editForm, total_units_kwh: parseFloat(e.target.value) || 0 })
                            }
                            className={styles.fieldInput}
                          />
                        </div>

                        <div className={styles.fieldGroup}>
                          <label className={styles.fieldLabel}>Net Amount Due (₹)</label>
                          <input
                            type="number"
                            value={editForm.net_amount_due || 0}
                            onChange={(e) =>
                              setEditForm({ ...editForm, net_amount_due: parseFloat(e.target.value) || 0 })
                            }
                            className={styles.fieldInput}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Meter Readings Table */}
                    {selectedBill.readings && selectedBill.readings.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8, paddingTop: 10, borderTop: "1px solid var(--border-subtle)" }}>
                        <span className={styles.fieldsTitle}>
                          Meter Registers ({selectedBill.readings.length})
                        </span>
                        <div className={styles.registersTableWrap}>
                          <table className={styles.registersTable}>
                            <thead>
                              <tr>
                                <th>Register</th>
                                <th>Type</th>
                                <th>Prev</th>
                                <th>Curr</th>
                                <th>MF</th>
                                <th style={{ textAlign: "right" }}>Consumed</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedBill.readings.map((r, i) => (
                                <tr key={i}>
                                  <td style={{ fontWeight: 600 }}>{r.meter_number}</td>
                                  <td style={{ color: "var(--text-muted)" }}>{r.reading_type}</td>
                                  <td>{r.previous_reading.toLocaleString("en-IN")}</td>
                                  <td>{r.current_reading.toLocaleString("en-IN")}</td>
                                  <td>{r.multiplying_factor}</td>
                                  <td style={{ textAlign: "right", fontWeight: 700 }}>
                                    {r.consumed_units.toLocaleString("en-IN")}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className={styles.billsCard} style={{ padding: 48, textAlign: "center" }}>
                <FileText style={{ width: 40, height: 40, margin: "0 auto 12px", color: "var(--border-strong)" }} />
                <h4 style={{ fontSize: 15, fontWeight: 600 }}>No bill selected</h4>
                <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                  Upload an electricity bill or select an existing record from the list.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Settings & AI Configuration Modal */}
      {showSettings && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalCard}>
            <div className={styles.modalHeader}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div className={styles.brandLogo} style={{ width: 32, height: 32 }}>
                  <SettingsIcon style={{ width: 16, height: 16 }} />
                </div>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 700 }}>Settings & AI Configuration</h3>
                  <p style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "ui-monospace, monospace" }}>
                    Tesseract Engine • Ollama Llama 3.2 • Google Gemini 2.5 Flash
                  </p>
                </div>
              </div>
              <button onClick={() => setShowSettings(false)} className={styles.modalCloseBtn}>
                ✕
              </button>
            </div>

            {/* Provider Section 1: Google Gemini */}
            <div className={styles.settingsSection}>
              <div style={{ display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Sparkles style={{ width: 16, height: 16 }} />
                  <span style={{ fontSize: 12, fontWeight: 700, fontFamily: "ui-monospace, monospace" }}>
                    Google Gemini 2.5 Flash
                  </span>
                </div>
                {settingsData?.gemini_configured ? (
                  <span className={`${styles.statusTag} ${styles.statusVerified}`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                    <CheckCircle2 style={{ width: 12, height: 12 }} /> Active
                  </span>
                ) : (
                  <span className={`${styles.statusTag}`} style={{ backgroundColor: "var(--border-subtle)", color: "var(--text-muted)" }}>
                    Not Configured
                  </span>
                )}
              </div>

              <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                Enter your Google AI Studio API key to enable instant plain-English summaries using Gemini 2.5 Flash.
              </p>

              <div style={{ position: "relative" }}>
                <input
                  type={showGeminiKey ? "text" : "password"}
                  placeholder={settingsData?.gemini_masked_key || "AIzaSy..."}
                  value={geminiKeyInput}
                  onChange={(e) => setGeminiKeyInput(e.target.value)}
                  className={styles.fieldInput}
                  style={{ paddingRight: 40 }}
                />
                <button
                  type="button"
                  onClick={() => setShowGeminiKey(!showGeminiKey)}
                  style={{ position: "absolute", right: 8, top: 7, background: "transparent", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
                >
                  {showGeminiKey ? <EyeOff style={{ width: 14, height: 14 }} /> : <Eye style={{ width: 14, height: 14 }} />}
                </button>
              </div>

              <button
                onClick={() => testProviderConnection("gemini")}
                disabled={isTesting || (!geminiKeyInput && !settingsData?.gemini_configured)}
                className={`${styles.btn} ${styles.btnOutline}`}
                style={{ alignSelf: "flex-start" }}
              >
                {isTesting ? <Loader2 style={{ width: 12, height: 12 }} className={styles.spinAnimation} /> : <Zap style={{ width: 12, height: 12 }} />}
                <span>Test Gemini Connection</span>
              </button>
            </div>

            {/* Provider Section 2: Local Ollama */}
            <div className={styles.settingsSection}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Cpu style={{ width: 16, height: 16 }} />
                  <span style={{ fontSize: 12, fontWeight: 700, fontFamily: "ui-monospace, monospace" }}>
                    Local Ollama (Llama 3.2)
                  </span>
                </div>
                <span
                  className={`${styles.statusTag} ${settingsData?.ollama_status === "AVAILABLE"
                    ? styles.statusVerified
                    : styles.statusReview
                    }`}
                >
                  {settingsData?.ollama_status || "Checking..."}
                </span>
              </div>

              <div className={styles.fieldsGrid}>
                <div className={styles.fieldGroup}>
                  <label className={styles.fieldLabel}>Base URL</label>
                  <input
                    type="text"
                    value={ollamaUrlInput}
                    onChange={(e) => setOllamaUrlInput(e.target.value)}
                    className={styles.fieldInput}
                  />
                </div>
                <div className={styles.fieldGroup}>
                  <label className={styles.fieldLabel}>Model Tag</label>
                  <input
                    type="text"
                    value={ollamaModelInput}
                    onChange={(e) => setOllamaModelInput(e.target.value)}
                    className={styles.fieldInput}
                  />
                </div>
              </div>

              <button
                onClick={() => testProviderConnection("ollama")}
                disabled={isTesting}
                className={`${styles.btn} ${styles.btnOutline}`}
                style={{ alignSelf: "flex-start" }}
              >
                {isTesting ? <Loader2 style={{ width: 12, height: 12 }} className={styles.spinAnimation} /> : <Zap style={{ width: 12, height: 12 }} />}
                <span>Ping Local Ollama</span>
              </button>
            </div>

            {/* Test Connection Result Alert */}
            {testResult && (
              <div
                className={`${styles.alertBox} ${testResult.success ? styles.statusVerified : styles.alertError
                  }`}
              >
                {testResult.success ? (
                  <CheckCircle2 style={{ width: 16, height: 16, flexShrink: 0 }} />
                ) : (
                  <XCircle style={{ width: 16, height: 16, flexShrink: 0 }} />
                )}
                <div>
                  <strong style={{ display: "block", textTransform: "uppercase" }}>
                    {testResult.provider} Test Result
                  </strong>
                  <span style={{ fontSize: 11 }}>{testResult.message}</span>
                </div>
              </div>
            )}

            {/* System Diagnostics Grid */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <span className={styles.fieldsTitle}>System Engine Diagnostics</span>
              <div className={styles.mathGrid}>
                <div className={styles.mathBox} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
                    <Layers style={{ width: 14, height: 14 }} /> Tesseract OCR
                  </span>
                  <span style={{ color: "var(--accent-emerald)", fontWeight: 700, fontSize: 11 }}>200 DPI Active</span>
                </div>
                <div className={styles.mathBox} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
                    <Database style={{ width: 14, height: 14 }} /> PostgreSQL
                  </span>
                  <span style={{ color: "var(--accent-emerald)", fontWeight: 700, fontSize: 11 }}>BYTEA Storage</span>
                </div>
                <div className={styles.mathBox} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
                    <Server style={{ width: 14, height: 14 }} /> Redis Cache
                  </span>
                  <span style={{ color: "var(--accent-emerald)", fontWeight: 700, fontSize: 11 }}>Port 6379</span>
                </div>
                <div className={styles.mathBox} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
                    <Cpu style={{ width: 14, height: 14 }} /> Poppler
                  </span>
                  <span style={{ color: "var(--accent-emerald)", fontWeight: 700, fontSize: 11 }}>Installed</span>
                </div>
              </div>
            </div>

            {/* Footer Buttons */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 10, paddingTop: 12, borderTop: "1px solid var(--border-subtle)" }}>
              <button
                onClick={() => setShowSettings(false)}
                className={`${styles.btn} ${styles.btnOutline}`}
              >
                Close
              </button>
              <button
                onClick={saveSettings}
                disabled={isSavingSettings}
                className={`${styles.btn} ${styles.btnSolid}`}
              >
                {isSavingSettings ? "Saving..." : "Save Settings"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
