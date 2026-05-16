/**
 * useAnalysis.js
 * Custom hook — encapsulates the /analyze API call and all state.
 *
 * Fix applied:
 *   - BUG: The axios POST had no timeout. If the backend hangs (e.g. Groq API
 *     slow, PDF extraction stalls), the UI would spin forever with no way out.
 *     Fixed by adding a 60-second timeout. If the backend legitimately takes
 *     longer (unusual), the user sees a clear error instead of an infinite spinner.
 */

import { useState } from "react";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

// FIX: Set a generous but finite timeout. Groq LLM calls + graph building
// typically take 10-25 seconds. 60 seconds gives plenty of headroom while
// still producing a user-visible error if something goes wrong.
const REQUEST_TIMEOUT_MS = 60_000;

export function useAnalysis() {
  const [resume, setResume] = useState(null);
  const [jd, setJd] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyze = async () => {
    if (!resume || !jd) {
      setError("Please upload both a Resume PDF and a Job Description PDF.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      form.append("resume", resume);
      form.append("jd", jd);

      const { data } = await axios.post(`${API_BASE}/analyze`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        // FIX: Add timeout so the spinner doesn't run forever if backend hangs.
        timeout: REQUEST_TIMEOUT_MS,
      });
      setResult(data);
    } catch (err) {
      // FIX: Distinguish timeout errors from other failures for better UX.
      let msg;
      if (err.code === "ECONNABORTED" || err.message?.toLowerCase().includes("timeout")) {
        msg = "Request timed out after 60 seconds. The backend may be overloaded — please try again.";
      } else {
        msg =
          err.response?.data?.detail ||
          err.message ||
          "Analysis failed. Check the backend logs.";
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setResume(null);
    setJd(null);
    setResult(null);
    setError(null);
  };

  return { resume, setResume, jd, setJd, result, loading, error, analyze, reset };
}
