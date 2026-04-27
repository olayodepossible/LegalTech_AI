"use client";

import {
  getRagDocuments,
  logActivityRemote,
  postRagDocumentUpload,
  type RagUploadResult,
} from "@/lib/api";
import { useAuth, useUser } from "@clerk/react";
import { useCallback, useEffect, useRef, useState } from "react";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function formatUploadedAt(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function DownloadIcon(props: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className={props.className}
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
      />
    </svg>
  );
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
  const [documents, setDocuments] = useState<
    Awaited<ReturnType<typeof getRagDocuments>>
  >([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!userId) return;
    logActivityRemote(getToken, "visit_rag", "Opened RAG documents");
  }, [userId, getToken]);

  const loadDocuments = useCallback(async () => {
    if (!userId) return;
    setListError(null);
    setListLoading(true);
    try {
      const rows = await getRagDocuments(() => getToken());
      setDocuments(rows);
    } catch (e) {
      setListError(e instanceof Error ? e.message : "Could not load documents");
      setDocuments([]);
    } finally {
      setListLoading(false);
    }
  }, [userId, getToken]);

  useEffect(() => {
    if (!userId) return;
    void loadDocuments();
  }, [userId, loadDocuments]);

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
      await loadDocuments();
      logActivityRemote(
        getToken,
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
          Upload documents
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Upload legal and legal cases documents to be used for future reference and guidance.
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
              {result.download_url ? (
                <div>
                  <dt className="text-zinc-500">Download</dt>
                  <dd className="mt-0.5">
                    <a
                      href={result.download_url}
                      className="font-medium text-indigo-600 underline hover:text-indigo-500 dark:text-indigo-400"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open / download file
                    </a>
                    <p className="mt-1 text-xs text-zinc-500">
                      This link expires after a limited time (set by the API).
                    </p>
                  </dd>
                </div>
              ) : null}
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

      <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            Your documents
          </h2>
          <button
            type="button"
            onClick={() => void loadDocuments()}
            disabled={listLoading}
            className="text-xs font-medium text-indigo-600 hover:text-indigo-500 disabled:opacity-50 dark:text-indigo-400"
          >
            {listLoading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Files you uploaded in this app (per your account). Use the download
          icon to open a time-limited link.
        </p>

        {listError ? (
          <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/40 dark:text-amber-100">
            {listError}
          </p>
        ) : null}

        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[32rem] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-zinc-700">
                <th className="py-2 pr-4 font-medium text-zinc-600 dark:text-zinc-400">
                  Name
                </th>
                <th className="py-2 pr-4 font-medium text-zinc-600 dark:text-zinc-400">
                  Uploaded
                </th>
                <th className="py-2 pr-4 font-medium text-zinc-600 dark:text-zinc-400">
                  Size
                </th>
                <th className="w-12 py-2 text-right font-medium text-zinc-600 dark:text-zinc-400">
                  <span className="sr-only">Download</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {listLoading && documents.length === 0 ? (
                <tr>
                  <td
                    colSpan={4}
                    className="py-6 text-zinc-500 dark:text-zinc-400"
                  >
                    Loading…
                  </td>
                </tr>
              ) : !listLoading && documents.length === 0 ? (
                <tr>
                  <td
                    colSpan={4}
                    className="py-6 text-zinc-500 dark:text-zinc-400"
                  >
                    No documents yet. Upload a file above to see it here.
                  </td>
                </tr>
              ) : (
                documents.map((row) => (
                  <tr
                    key={row.s3_key}
                    className="border-b border-zinc-100 dark:border-zinc-800/80"
                  >
                    <td className="max-w-[16rem] py-2.5 pr-4">
                      <span
                        className="block truncate font-medium text-zinc-900 dark:text-zinc-100"
                        title={row.name}
                      >
                        {row.name}
                      </span>
                    </td>
                    <td className="whitespace-nowrap py-2.5 pr-4 text-zinc-600 dark:text-zinc-300">
                      {formatUploadedAt(row.last_modified)}
                    </td>
                    <td className="whitespace-nowrap py-2.5 pr-4 text-zinc-600 dark:text-zinc-300">
                      {formatBytes(row.size_bytes)}
                    </td>
                    <td className="py-2.5 text-right">
                      {row.download_url ? (
                        <a
                          href={row.download_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-indigo-600 transition-colors hover:bg-indigo-50 hover:text-indigo-700 dark:text-indigo-400 dark:hover:bg-indigo-950/50 dark:hover:text-indigo-300"
                          title={`Download ${row.name}`}
                          aria-label={`Download ${row.name}`}
                        >
                          <DownloadIcon className="h-5 w-5" />
                        </a>
                      ) : (
                        <span
                          className="inline-flex h-9 w-9 items-center justify-center text-zinc-300 dark:text-zinc-600"
                          title="Download link unavailable"
                        >
                          —
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
