document.getElementById('jobForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const jobUrl = document.getElementById('jobUrl').value.trim();
  const resumeUrl = document.getElementById('resumeUrl').value.trim();
  const suggestionsDiv = document.getElementById('suggestions');
  const revisedPre = document.getElementById('revised');
  const submitBtn = e.target.querySelector('button[type="submit"]');

  // Disable button and show loading state
  submitBtn.disabled = true;
  const originalText = submitBtn.textContent;
  submitBtn.textContent = 'Generating...';

  suggestionsDiv.innerHTML = '<div class="flex items-center gap-2 text-gray-600"><span class="animate-spin text-lg">⚙️</span> Analyzing job posting and generating suggestions...</div>';
  revisedPre.textContent = '';

  try {
    const res = await fetch('/api/suggestions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_posting_url: jobUrl, resume_pdf_url: resumeUrl })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const errorMsg = err.detail || res.statusText;
      suggestionsDiv.innerHTML = `<div class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg"><strong>Error:</strong> ${errorMsg}</div>`;
      revisedPre.textContent = '';
      return;
    }

    const data = await res.json();
    
    // Display suggestions
    if (data.suggestion_content) {
      suggestionsDiv.innerHTML = `<div class="bg-blue-50 border border-blue-200 rounded-lg p-4"><pre class="text-sm text-gray-800 whitespace-pre-wrap">${escapeHtml(data.suggestion_content)}</pre></div>`;
    } else {
      suggestionsDiv.innerHTML = '<p class="text-gray-500">No suggestions available</p>';
    }
    
    // Display revised resume
    if (data.revised_resume_content) {
      revisedPre.textContent = data.revised_resume_content;
    } else {
      revisedPre.textContent = 'No revised resume content available';
    }
  } catch (err) {
    suggestionsDiv.innerHTML = `<div class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg"><strong>Request failed:</strong> ${escapeHtml(err.message)}</div>`;
    revisedPre.textContent = '';
  } finally {
    // Re-enable button
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
});

// Helper function to escape HTML
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}
