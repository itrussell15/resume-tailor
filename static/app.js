let lastSuggestionData = null;

document.addEventListener('DOMContentLoaded', () => {
  const jobForm = document.getElementById('jobForm');
  if (!jobForm) {
    console.error('jobForm not found in DOM');
    return;
  }

  // Wire the generate button to call /api/generate with the last suggestions
  const genBtn = document.getElementById('generateResumeBtn');
  if (genBtn) {
    genBtn.addEventListener('click', async () => {
      if (!lastSuggestionData) {
        alert('No suggestions available to generate a resume from.');
        return;
      }
      genBtn.disabled = true;
      const origText = genBtn.textContent;
      genBtn.textContent = 'Generating...';
      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ suggestion: lastSuggestionData })
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          const errorMsg = err.detail || res.statusText;
          alert('Generate failed: ' + errorMsg);
          return;
        }

        const result = await res.json();
        const url = result.generated_resume_url;
        if (url) {
          window.open(url, '_blank');
        } else {
          alert('Generate succeeded.');
        }
      } catch (err) {
        console.error('Generate request failed', err);
        alert('Generate request failed: ' + (err.message || err));
      } finally {
        genBtn.disabled = false;
        genBtn.textContent = origText;
      }
    });
  }

  jobForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const jobUrlEl = document.getElementById('jobUrl');
    if (!jobUrlEl) {
      console.error('jobUrl input not found');
      return;
    }
    const jobUrl = (jobUrlEl.value || '').trim();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (!submitBtn) {
      console.error('submit button not found');
    }

  // Disable button and show loading state
  submitBtn.disabled = true;
  const originalText = submitBtn.textContent;
  submitBtn.textContent = 'Generating...';

  // Hide all sections initially
  document.getElementById('jobDetailsSection').classList.add('hidden');
  document.getElementById('missingSectionSection').classList.add('hidden');
  document.getElementById('suggestionsSection').classList.add('hidden');
  document.getElementById('generateSection')?.classList.add('hidden');

    const statusDiv = document.getElementById('statusMessages');
    if (statusDiv) {
      statusDiv.innerHTML = '<div class="bg-blue-50 border border-blue-200 rounded-lg p-4"><div class="flex items-center gap-2 text-gray-600"><span class="animate-spin text-lg">⚙️</span> Analyzing job posting and generating suggestions...</div></div>';
      statusDiv.classList.remove('hidden');
    } else {
      console.warn('statusMessages element not found');
    }

  try {
    console.debug('Submitting job posting URL to /api/suggestions', { jobUrl});
    const res = await fetch('/api/suggestions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_posting_url: jobUrl })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const errorMsg = err.detail || res.statusText;
      statusDiv.innerHTML = `<div class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg"><strong>Error:</strong> ${errorMsg}</div>`;
      return;
    }

    const data = await res.json();
    // store last suggestions so the generate button can use them
    lastSuggestionData = data;
    statusDiv.classList.add('hidden');
    
    // Display Job Details
    if (data.suggestion_content?.job_details) {
      const jobDetails = data.suggestion_content.job_details;
      document.getElementById('jobRole').textContent = jobDetails.role || 'N/A';
      document.getElementById('jobCompany').textContent = jobDetails.company || 'N/A';
      document.getElementById('jobDetailsSection').classList.remove('hidden');
    }
    
    // Display Missing Skill
    if (data.suggestion_content?.missing_skill) {
      const missingSkillDiv = document.getElementById('missingSkill');
      missingSkillDiv.innerHTML = marked.parse(data.suggestion_content.missing_skill);
      missingSkillDiv.classList.add('markdown-content');
      document.getElementById('missingSectionSection').classList.remove('hidden');
    }
    
    // Display Resume Changes (suggestions)
    if (data.suggestion_content?.resume_changes && Array.isArray(data.suggestion_content.resume_changes)) {
      const suggestionsDiv = document.getElementById('suggestions');
      suggestionsDiv.innerHTML = '';
      
      data.suggestion_content.resume_changes.forEach((change, index) => {
        const changeContainer = document.createElement('div');
        changeContainer.className = 'border border-gray-300 rounded-lg p-4 bg-gray-50';
        
        const header = document.createElement('h3');
        header.className = 'font-bold text-lg mb-2 text-gray-800';
        header.textContent = change.company || `Change ${index + 1}`;
        changeContainer.appendChild(header);
        
        if (change.bullet_points && Array.isArray(change.bullet_points)) {
          const ul = document.createElement('ul');
          ul.className = 'list-disc list-inside space-y-1 text-gray-700';
          change.bullet_points.forEach(point => {
            const li = document.createElement('li');
            li.innerHTML = marked.parseInline(point);
            ul.appendChild(li);
          });
          changeContainer.appendChild(ul);
        }
        
        suggestionsDiv.appendChild(changeContainer);
      });
      
      document.getElementById('suggestionsSection').classList.remove('hidden');
      // Reveal the generate section so user can create a new resume from suggestions
      document.getElementById('generateSection')?.classList.remove('hidden');
    }
    } catch (err) {
      console.error('Error during suggestions request', err);
      if (statusDiv) {
        const msg = (err && err.message) ? escapeHtml(err.message) : 'Unknown error';
        statusDiv.innerHTML = `<div class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg"><strong>Request failed:</strong> ${msg}</div>`;
        statusDiv.classList.remove('hidden');
      }
    } finally {
      // Re-enable button
      if (submitBtn) submitBtn.disabled = false;
      if (submitBtn) submitBtn.textContent = originalText;
    }
  });
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
