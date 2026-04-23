"use client";

import { postRagDocumentUpload, type RagUploadResult } from "@/lib/api";
import { logActivity } from "@/lib/local-store";
import { useAuth, useUser } from "@clerk/nextjs";
import { useCallback, useEffect, useRef, useState } from "react";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function RagDocPage() {
  const { user, isLoaded } = useUser();
  const { getToken } = useAuth();
  const userId = user?.id;
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RagUploadResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!userId) return;
    logActivity(userId, "visit_rag", "Opened RAG documents");
  }, [userId]);

  const onFiles = useCallback((list: FileList | null) => {
    const f = list?.[0];
    if (f) {
      setFile(f);
      setError(null);
      setResult(null);
    }
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(false);
      onFiles(e.dataTransfer.files);
    },
    [onFiles],
  );

  async function upload() {
    if (!file || !userId) return;
    setSending(true);
    setError(null);
    setResult(null);
    try {
      const payload = await postRagDocumentUpload(file, () => getToken());
      setResult(payload);
      logActivity(
        userId,
        "document_upload",
        "RAG document uploaded to S3",
        payload.s3_key,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setSending(false);
    }
  }

  if (!isLoaded || !userId) return null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          RAG documents
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Flow: upload to S3, optional SQS job, worker processes chunks, then
          S3 Vectors. Configure the API with{" "}
          <code className="rounded bg-zinc-200/80 px-1 dark:bg-zinc-800">
            RAG_DOCUMENTS_BUCKET
          </code>{" "}
          and an ingestion queue (see{" "}
          <code className="rounded bg-zinc-200/80 px-1 dark:bg-zinc-800">
            RAG_INGESTION_QUEUE_URL
          </code>{" "}
          or <code className="rounded bg-zinc-200/80 px-1">SQS_QUEUE_URL</code>
          ), and run the ingestion worker.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            Upload
          </h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            PDF, text, or other formats your ingest pipeline accepts.
          </p>

          <input
            ref={inputRef}
            type="file"
            className="hidden"
            onChange={(e) => onFiles(e.target.files)}
          />

          <div
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDragEnter={() => setDrag(true)}
            onDragLeave={() => setDrag(false)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={[
              "mt-4 flex min-h-[200px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors",
              drag
                ? "border-indigo-400 bg-indigo-50/80 dark:border-indigo-500/50 dark:bg-indigo-950/30"
                : "border-zinc-200 bg-zinc-50/50 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-950/40 dark:hover:border-zinc-600",
            ].join(" ")}
          >
            <svg
              className="mb-2 h-10 w-10 text-zinc-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M12 16V4m0 0L8 8m4-4 4 4" />
              <path d="M4 20h16" />
            </svg>
            <p className="text-sm font-medium text-zinc-700 dark:text-zinc-200">
              Drop a file here or click to browse
            </p>
            <p className="mt-1 text-xs text-zinc-500">One file per upload</p>
          </div>

          {file ? (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 text-sm dark:border-zinc-800 dark:bg-zinc-950/50">
              <span className="truncate font-medium text-zinc-800 dark:text-zinc-200">
                {file.name}
              </span>
              <span className="shrink-0 text-zinc-500">
                {formatBytes(file.size)}
              </span>
            </div>
          ) : null}

          {error ? (
            <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900 dark:border-rose-900/40 dark:bg-rose-950/40 dark:text-rose-100">
              {error}
            </p>
          ) : null}

          <button
            type="button"
            disabled={!file || sending}
            onClick={() => void upload()}
            className="mt-4 w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {sending ? "Uploading…" : "Upload to S3"}
          </button>
        </section>

        <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            Result
          </h2>
          {result ? (
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="text-zinc-500">Ingestion queue</dt>
                <dd className="mt-0.5 text-zinc-900 dark:text-zinc-100">
                  {result.ingestion_queued
                    ? "Job sent to SQS (worker indexes into the vector store)."
                    : "Not queued. Set RAG_INGESTION_QUEUE_URL or SQS_QUEUE_URL, or see API logs if send failed; file is still in S3."}
                </dd>
              </div>
              {result.sqs_message_id ? (
                <div>
                  <dt className="text-zinc-500">SQS message</dt>
                  <dd className="mt-0.5 font-mono text-xs break-all text-zinc-900 dark:text-zinc-100">
                    {result.sqs_message_id}
                  </dd>
                </div>
              ) : null}
              <div>
                <dt className="text-zinc-500">Document ID</dt>
                <dd className="mt-0.5 font-mono text-xs break-all text-zinc-900 dark:text-zinc-100">
                  {result.document_id}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">Bucket</dt>
                <dd className="mt-0.5 font-mono text-xs break-all text-zinc-900 dark:text-zinc-100">
                  {result.bucket}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">S3 key</dt>
                <dd className="mt-0.5 font-mono text-xs break-all text-zinc-900 dark:text-zinc-100">
                  {result.s3_key}
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">Size</dt>
                <dd className="mt-0.5 text-zinc-900 dark:text-zinc-100">
                  {formatBytes(result.size_bytes)}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="mt-4 text-sm text-zinc-500 dark:text-zinc-400">
              After a successful upload, object details appear here.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
