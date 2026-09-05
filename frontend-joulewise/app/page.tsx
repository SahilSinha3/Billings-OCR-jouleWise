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
} from "lucide-react";
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

  const fileInputRef = useRef<HTMLInputElement>(null);

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
    const interval = setInterval(fetchBills, 3000);
    return () => clearInterval(interval);
  }, [selectedBill?.id]);

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
    <div className="min-h-screen bg-[#050505] text-zinc-100 font-sans antialiased selection:bg-zinc-700 selection:text-white">
      {/* Sleek Apple-Style Monochrome Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-black/85 border-b border-zinc-800/80 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white text-black flex items-center justify-center font-bold shadow-sm">
              <Zap className="w-4 h-4 fill-black text-black" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-base tracking-tight text-white">JouleWise</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
                  Enterprise OCR
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 font-mono hidden sm:block">
                Tesseract Engine • PostgreSQL BYTEA Storage • Redis Cache
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {bills.length > 0 && (
              <button
                onClick={clearAllBills}
                className="text-xs text-zinc-400 hover:text-red-400 px-3 py-1.5 rounded-lg border border-zinc-800 hover:border-red-900/50 bg-zinc-900/50 transition-colors flex items-center gap-1.5 font-mono"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear All
              </button>
            )}

            <button
              onClick={() => {
                fetchSettings();
                setShowSettings(true);
              }}
              className="text-xs text-zinc-300 hover:text-white px-3 py-1.5 rounded-lg border border-zinc-800 hover:border-zinc-600 bg-zinc-900 transition-colors flex items-center gap-1.5 font-mono shadow-sm"
            >
              <SettingsIcon className="w-3.5 h-3.5" />
              <span>Settings & AI</span>
              {settingsData?.gemini_configured && (
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Upload & Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Multi-File Ingestion & Bill List (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            {/* Bulk Dropzone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`cursor-pointer p-6 rounded-xl border border-dashed transition-all text-center flex flex-col items-center justify-center gap-3 ${
                isDragging
                  ? "border-white bg-zinc-900 scale-[1.01]"
                  : "border-zinc-800 hover:border-zinc-600 bg-zinc-950/80 hover:bg-zinc-900/40"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files) {
                    handleFileUpload(e.target.files);
                  }
                }}
              />

              <div className="w-11 h-11 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-white shadow-inner">
                {isUploading ? (
                  <RefreshCw className="w-5 h-5 animate-spin text-white" />
                ) : (
                  <UploadCloud className="w-5 h-5 text-white" />
                )}
              </div>

              <div>
                <div className="text-sm font-semibold text-white">
                  {isUploading ? "Extracting via Tesseract..." : "Upload Bills (Single or Bulk)"}
                </div>
                <div className="text-xs text-zinc-500 mt-0.5">
                  Drag & drop PDFs or images • Zero local disk persistence
                </div>
              </div>

              {uploadError && (
                <div className="text-xs text-red-400 bg-red-950/40 border border-red-900/50 px-3 py-1.5 rounded mt-1">
                  {uploadError}
                </div>
              )}
            </div>

            {/* Bill Navigation List */}
            <div className="rounded-xl border border-zinc-800/80 bg-zinc-950 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5" />
                  Processed Bills ({bills.length})
                </span>
                <button
                  onClick={fetchBills}
                  className="text-xs text-zinc-500 hover:text-white transition-colors flex items-center gap-1 font-mono"
                >
                  <RefreshCw className="w-3 h-3" /> Refresh
                </button>
              </div>

              <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
                {bills.length === 0 ? (
                  <div className="text-center py-12 text-zinc-600 text-xs font-mono">
                    No bills ingested yet. Upload any electricity bill above.
                  </div>
                ) : (
                  bills.map((bill) => {
                    const isSelected = selectedBill?.id === bill.id;
                    const isRejected = bill.status === "REJECTED_NON_BILL" || bill.is_valid_bill === false;
                    const isVerified = bill.status === "VERIFIED";

                    return (
                      <div
                        key={bill.id}
                        onClick={() => handleSelectBill(bill)}
                        className={`group relative cursor-pointer p-3.5 rounded-lg border transition-all text-left ${
                          isSelected
                            ? "bg-zinc-900 border-zinc-500 shadow-md"
                            : "bg-zinc-900/40 border-zinc-800/80 hover:bg-zinc-900/70 hover:border-zinc-700"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="space-y-1 max-w-[70%]">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300">
                                {bill.discom_code}
                              </span>
                              <span className="text-xs font-semibold text-white tracking-tight truncate">
                                {bill.consumer_name || "Consumer"}
                              </span>
                            </div>
                            <div className="text-[11px] text-zinc-400 font-mono truncate">
                              Acc: {bill.consumer_number || "N/A"}
                            </div>
                          </div>

                          <div className="flex flex-col items-end gap-1">
                            <div className="text-xs font-bold text-white font-mono">
                              ₹{(bill.net_amount_due || 0).toLocaleString("en-IN")}
                            </div>
                            <div className="flex items-center gap-1.5">
                              <span
                                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                                  isRejected
                                    ? "bg-red-950/80 text-red-400 border-red-900/50"
                                    : isVerified
                                    ? "bg-emerald-950/80 text-emerald-400 border-emerald-800/50"
                                    : "bg-amber-950/80 text-amber-400 border-amber-800/50"
                                }`}
                              >
                                {isRejected ? "Invalid Doc" : isVerified ? "Verified" : "Review"}
                              </span>
                              <button
                                onClick={(e) => deleteBill(bill.id, e)}
                                title="Delete this bill"
                                className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-red-400 p-0.5 transition-opacity"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Side-by-Side Detailed Workspace (8 cols) */}
          <div className="lg:col-span-8">
            {selectedBill ? (
              <div className="space-y-6">
                {/* Rejection Alert Banner if Non-Bill */}
                {(selectedBill.status === "REJECTED_NON_BILL" || selectedBill.is_valid_bill === false) && (
                  <div className="rounded-xl border border-red-900/80 bg-red-950/40 p-4 text-red-200 flex items-start gap-3 shadow-lg">
                    <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-semibold text-sm text-red-300">
                        Document Classification Guardrail Triggered
                      </h4>
                      <p className="text-xs text-red-300/80 mt-1">
                        {selectedBill.validation_error ||
                          "This document was recognized as a technical manual, register map, or datasheet rather than a state electricity bill."}
                      </p>
                    </div>
                  </div>
                )}

                {/* Plain-English Bill Summary Card */}
                {selectedBill.bill_summary ? (
                  <div className="rounded-xl border border-zinc-700/80 bg-gradient-to-r from-zinc-900 to-zinc-950 p-4.5 shadow-md flex items-start gap-3.5">
                    <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center shrink-0">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-white tracking-wide uppercase font-mono">
                          Plain-English Summary
                        </span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400">
                          AI Generated
                        </span>
                      </div>
                      <p className="text-xs text-zinc-200 leading-relaxed">
                        {selectedBill.bill_summary}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3.5 text-xs text-zinc-400 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-zinc-400" />
                      <span>
                        Pure Tesseract OCR extracted all bill fields below. Configure Gemini or Ollama in Settings to enable plain-English summaries.
                      </span>
                    </div>
                    <button
                      onClick={() => setShowSettings(true)}
                      className="text-xs text-white hover:underline font-mono"
                    >
                      Settings →
                    </button>
                  </div>
                )}

                {/* Split Workspace: Document Stream on Left, Verification on Right */}
                <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
                  {/* Left Half: Document Viewer / Raw OCR Text (6 cols on XL) */}
                  <div className="xl:col-span-6 rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden shadow-lg flex flex-col h-[700px]">
                    <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-900 border-b border-zinc-800">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setActiveLeftTab("document")}
                          className={`text-xs font-mono px-3 py-1 rounded transition-colors ${
                            activeLeftTab === "document"
                              ? "bg-black text-white font-medium shadow-sm"
                              : "text-zinc-400 hover:text-white"
                          }`}
                        >
                          Document Preview
                        </button>
                        <button
                          onClick={() => setActiveLeftTab("raw_text")}
                          className={`text-xs font-mono px-3 py-1 rounded transition-colors ${
                            activeLeftTab === "raw_text"
                              ? "bg-black text-white font-medium shadow-sm"
                              : "text-zinc-400 hover:text-white"
                          }`}
                        >
                          Raw OCR Text
                        </button>
                      </div>

                      {activeLeftTab === "raw_text" && selectedBill.raw_extracted_text && (
                        <button
                          onClick={() => copyToClipboard(selectedBill.raw_extracted_text || "")}
                          className="text-xs text-zinc-400 hover:text-white flex items-center gap-1 font-mono transition-colors"
                        >
                          {copiedText ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          {copiedText ? "Copied" : "Copy"}
                        </button>
                      )}
                    </div>

                    <div className="flex-1 bg-black overflow-hidden relative">
                      {activeLeftTab === "document" ? (
                        <iframe
                          src={`${API_BASE_URL}/bills/${selectedBill.id}/file`}
                          title="Original Bill Preview"
                          className="w-full h-full border-0"
                        />
                      ) : (
                        <pre className="w-full h-full p-4 text-[11px] font-mono text-zinc-300 whitespace-pre-wrap overflow-auto leading-relaxed selection:bg-zinc-800">
                          {selectedBill.raw_extracted_text || "No OCR text extracted."}
                        </pre>
                      )}
                    </div>
                  </div>

                  {/* Right Half: Form & Mathematical Audit (6 cols on XL) */}
                  <div className="xl:col-span-6 rounded-xl border border-zinc-800 bg-zinc-950 p-5 space-y-5 shadow-lg max-h-[700px] overflow-y-auto">
                    {/* Header */}
                    <div className="flex items-start justify-between border-b border-zinc-800 pb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-medium">
                            {selectedBill.discom_code}
                          </span>
                          <h3 className="font-bold text-base text-white tracking-tight">
                            {selectedBill.consumer_name}
                          </h3>
                        </div>
                        <p className="text-xs text-zinc-400 mt-1">{selectedBill.discom_name}</p>
                      </div>

                      <div className="text-right">
                        <div className="text-[10px] text-zinc-400 font-mono">Net Amount Due</div>
                        <div className="text-xl font-bold font-mono text-white">
                          ₹{(selectedBill.net_amount_due || 0).toLocaleString("en-IN")}
                        </div>
                      </div>
                    </div>

                    {/* Mathematical Audit Card */}
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                          Mathematical Audit
                        </span>
                        <div className="flex items-center gap-1.5">
                          {selectedBill.is_math_verified ? (
                            <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800/60 text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Verified Pass
                            </span>
                          ) : (
                            <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-950 border border-amber-800/60 text-amber-400 flex items-center gap-1">
                              <AlertTriangle className="w-3.5 h-3.5" /> Flagged Review
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                        <div className="bg-black/60 p-2 rounded border border-zinc-800/60 flex items-center justify-between">
                          <span className="text-zinc-400">Active Units:</span>
                          <span className="text-white">
                            {selectedBill.total_units_kwh?.toLocaleString("en-IN")} kWh
                          </span>
                        </div>
                        <div className="bg-black/60 p-2 rounded border border-zinc-800/60 flex items-center justify-between">
                          <span className="text-zinc-400">Power Factor:</span>
                          <span className="text-white">{selectedBill.power_factor ?? "N/A"}</span>
                        </div>
                      </div>

                      {/* Discrepancies if any */}
                      {selectedBill.verification_details?.discrepancies &&
                        selectedBill.verification_details.discrepancies.length > 0 && (
                          <div className="space-y-1.5 pt-2 border-t border-zinc-800/80">
                            <span className="text-[11px] font-mono text-amber-400 font-semibold">
                              Audit Anomalies Detected:
                            </span>
                            {selectedBill.verification_details.discrepancies.map((d, i) => (
                              <div
                                key={i}
                                className="text-[11px] font-mono bg-amber-950/30 border border-amber-900/40 p-2 rounded text-amber-200"
                              >
                                <div>• {d.rule_name}</div>
                                <div className="text-[10px] text-amber-300/80 mt-0.5">
                                  Expected {d.expected_value} vs Extracted {d.reported_value} (Δ {d.discrepancy_delta})
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                    </div>

                    {/* Verified Editable Form */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                          Extracted Bill Fields
                        </span>
                        <button
                          onClick={handleSaveEdit}
                          disabled={isSavingEdit}
                          className="text-xs font-mono px-3 py-1 rounded bg-white text-black font-semibold hover:bg-zinc-200 transition-colors disabled:opacity-50"
                        >
                          {isSavingEdit ? "Saving..." : "Save & Re-verify"}
                        </button>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div className="space-y-1">
                          <label className="text-zinc-400 font-mono text-[11px]">Consumer Name</label>
                          <input
                            type="text"
                            value={editForm.consumer_name || ""}
                            onChange={(e) => setEditForm({ ...editForm, consumer_name: e.target.value })}
                            className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono focus:border-zinc-500 focus:outline-none"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-zinc-400 font-mono text-[11px]">Account / CA Number</label>
                          <input
                            type="text"
                            value={editForm.consumer_number || ""}
                            onChange={(e) => setEditForm({ ...editForm, consumer_number: e.target.value })}
                            className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono focus:border-zinc-500 focus:outline-none"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-zinc-400 font-mono text-[11px]">Bill Number</label>
                          <input
                            type="text"
                            value={editForm.bill_number || ""}
                            onChange={(e) => setEditForm({ ...editForm, bill_number: e.target.value })}
                            className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono focus:border-zinc-500 focus:outline-none"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-zinc-400 font-mono text-[11px]">Due Date</label>
                          <input
                            type="date"
                            value={editForm.due_date || ""}
                            onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value })}
                            className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono focus:border-zinc-500 focus:outline-none"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-zinc-400 font-mono text-[11px]">Total Units (kWh)</label>
                          <input
                            type="number"
                            value={editForm.total_units_kwh || ""}
                            onChange={(e) => setEditForm({ ...editForm, total_units_kwh: Number(e.target.value) })}
                            className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono focus:border-zinc-500 focus:outline-none"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-zinc-400 font-mono text-[11px]">Net Amount Due (₹)</label>
                          <input
                            type="number"
                            step="0.01"
                            value={editForm.net_amount_due || ""}
                            onChange={(e) => setEditForm({ ...editForm, net_amount_due: Number(e.target.value) })}
                            className="w-full bg-black border border-zinc-800 rounded px-2.5 py-1.5 text-white font-mono focus:border-zinc-500 focus:outline-none"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Meter Readings Table */}
                    {selectedBill.readings && selectedBill.readings.length > 0 && (
                      <div className="space-y-2 pt-2 border-t border-zinc-800">
                        <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
                          Meter Registers ({selectedBill.readings.length})
                        </span>
                        <div className="overflow-x-auto rounded border border-zinc-800">
                          <table className="w-full text-[11px] font-mono text-left">
                            <thead className="bg-zinc-900 text-zinc-400 border-b border-zinc-800">
                              <tr>
                                <th className="p-2">Register</th>
                                <th className="p-2">Type</th>
                                <th className="p-2 text-right">Prev</th>
                                <th className="p-2 text-right">Curr</th>
                                <th className="p-2 text-right">MF</th>
                                <th className="p-2 text-right">Consumed</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-zinc-800/60 bg-black/40">
                              {selectedBill.readings.map((r, idx) => (
                                <tr key={idx}>
                                  <td className="p-2 text-zinc-300">{r.meter_number}</td>
                                  <td className="p-2 text-zinc-300">{r.reading_type}</td>
                                  <td className="p-2 text-right text-zinc-400">{r.previous_reading?.toLocaleString("en-IN")}</td>
                                  <td className="p-2 text-right text-zinc-400">{r.current_reading?.toLocaleString("en-IN")}</td>
                                  <td className="p-2 text-right text-zinc-400">{r.multiplying_factor}</td>
                                  <td className="p-2 text-right text-white font-semibold">
                                    {r.consumed_units?.toLocaleString("en-IN")}
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
              </div>
            ) : (
              <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-12 text-center text-zinc-500 space-y-3">
                <FileText className="w-8 h-8 mx-auto text-zinc-600" />
                <div className="text-sm font-medium text-white">Select a bill from the left</div>
                <div className="text-xs font-mono text-zinc-500">
                  Document viewer, verified form, and mathematical audit will appear side-by-side.
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Settings Modal Dialog */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
          <div className="w-full max-w-xl bg-zinc-950 border border-zinc-800 rounded-2xl p-6 shadow-2xl space-y-6 animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-white text-black">
                  <SettingsIcon className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-white tracking-tight">AI & Engine Settings</h3>
                  <p className="text-xs text-zinc-400 font-mono">Configure Gemini 2.5 Flash & Local Ollama</p>
                </div>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-zinc-500 hover:text-white p-1 rounded-md transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {/* System Status Badges */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
              <div className="p-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 flex flex-col gap-1">
                <span className="text-zinc-400 flex items-center gap-1">
                  <Cpu className="w-3 h-3" /> Tesseract
                </span>
                <span className="text-emerald-400 font-semibold">Active & Local</span>
              </div>
              <div className="p-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 flex flex-col gap-1">
                <span className="text-zinc-400 flex items-center gap-1">
                  <Database className="w-3 h-3" /> Postgres 17
                </span>
                <span className="text-emerald-400 font-semibold">BYTEA Blob</span>
              </div>
              <div className="p-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 flex flex-col gap-1">
                <span className="text-zinc-400 flex items-center gap-1">
                  <Server className="w-3 h-3" /> Redis Cache
                </span>
                <span className="text-emerald-400 font-semibold">Port 6379</span>
              </div>
              <div className="p-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 flex flex-col gap-1">
                <span className="text-zinc-400 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> Ollama Llama
                </span>
                <span
                  className={settingsData?.ollama_status === "connected" ? "text-emerald-400 font-semibold" : "text-zinc-500"}
                >
                  {settingsData?.ollama_status === "connected" ? "Online" : "Offline"}
                </span>
              </div>
            </div>

            {/* Gemini 2.5 Flash Configuration */}
            <div className="space-y-2.5 pt-2 border-t border-zinc-800">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-white font-mono flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-zinc-300" />
                  Google Gemini 2.5 Flash API Key
                </label>
                {settingsData?.gemini_configured && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800/50 text-emerald-400">
                    Configured ({settingsData.gemini_masked_key})
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <input
                    type={showGeminiKey ? "text" : "password"}
                    placeholder={settingsData?.gemini_configured ? "Enter new key to update..." : "Paste GEMINI_API_KEY..."}
                    value={geminiKeyInput}
                    onChange={(e) => setGeminiKeyInput(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded-lg px-3 py-2 text-xs font-mono text-white placeholder:text-zinc-600 focus:border-zinc-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowGeminiKey(!showGeminiKey)}
                    className="absolute right-2.5 top-2.5 text-zinc-500 hover:text-white"
                  >
                    {showGeminiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => testProviderConnection("gemini")}
                  disabled={isTesting}
                  className="px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900 text-xs font-mono text-zinc-300 hover:text-white hover:border-zinc-600 transition-colors disabled:opacity-50"
                >
                  Test
                </button>
              </div>
              <p className="text-[11px] text-zinc-500">
                Optional: Used for plain-English 2-sentence bill summaries. If not configured or unavailable, pure Tesseract OCR operates with 100% functionality.
              </p>
            </div>

            {/* Local Ollama Configuration */}
            <div className="space-y-2.5 pt-2 border-t border-zinc-800">
              <label className="text-xs font-semibold text-white font-mono flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-zinc-300" />
                Local Ollama Engine Fallback
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono">Base URL</span>
                  <input
                    type="text"
                    value={ollamaUrlInput}
                    onChange={(e) => setOllamaUrlInput(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded-lg px-3 py-1.5 text-xs font-mono text-white focus:border-zinc-500 focus:outline-none mt-1"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-zinc-500 font-mono">Model Name</span>
                  <input
                    type="text"
                    value={ollamaModelInput}
                    onChange={(e) => setOllamaModelInput(e.target.value)}
                    className="w-full bg-black border border-zinc-800 rounded-lg px-3 py-1.5 text-xs font-mono text-white focus:border-zinc-500 focus:outline-none mt-1"
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => testProviderConnection("ollama")}
                  disabled={isTesting}
                  className="px-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900 text-xs font-mono text-zinc-300 hover:text-white hover:border-zinc-600 transition-colors disabled:opacity-50"
                >
                  Test Ollama Ping
                </button>
              </div>
            </div>

            {/* Live Connection Test Results */}
            {testResult && (
              <div
                className={`p-3 rounded-lg border text-xs font-mono ${
                  testResult.success
                    ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-300"
                    : "bg-red-950/40 border-red-900/60 text-red-300"
                }`}
              >
                {testResult.message}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
              <button
                type="button"
                onClick={() => setShowSettings(false)}
                className="px-4 py-2 rounded-lg text-xs font-mono text-zinc-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={saveSettings}
                disabled={isSavingSettings}
                className="px-5 py-2 rounded-lg bg-white text-black text-xs font-mono font-semibold hover:bg-zinc-200 transition-colors disabled:opacity-50"
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
