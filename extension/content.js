/**
 * Corporate DLP Guardian - Deep Main-World Interceptor
 * Intercepts Telegram Web's dynamic paperclip attachment menus ("Photo or Video", "Document"),
 * detached file inputs, Drag & Drop, and Clipboard Paste.
 */

(function () {
  'use strict';

  console.log('[Corporate DLP] Deep Main-World DLP Guardian active.');

  function showDLPAlert(fileName, reason) {
    const existing = document.getElementById('dlp-security-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'dlp-security-overlay';
    overlay.className = 'dlp-alert-overlay';

    overlay.innerHTML = `
      <div class="dlp-alert-card" role="dialog" aria-modal="true">
        <div class="dlp-alert-header">
          <svg class="dlp-alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <h2 class="dlp-alert-title">Corporate DLP: Upload Blocked</h2>
        </div>
        <div class="dlp-alert-body">
          <p class="dlp-alert-desc">
            Your file upload has been blocked by corporate security policy. 
            Proprietary 3D assets, archives, and unapproved file types cannot be sent.
          </p>
          <div class="dlp-alert-details">
            <div class="dlp-alert-row">
              <span class="dlp-alert-label">File:</span>
              <span class="dlp-alert-value">${escapeHtml(fileName || 'Unknown File')}</span>
            </div>
            <div class="dlp-alert-row">
              <span class="dlp-alert-label">Violation:</span>
              <span class="dlp-alert-value">${escapeHtml(reason || 'Blocked format')}</span>
            </div>
            <div class="dlp-alert-row">
              <span class="dlp-alert-label">Timestamp:</span>
              <span class="dlp-alert-value">${new Date().toLocaleString()}</span>
            </div>
          </div>
        </div>
        <div class="dlp-alert-footer">
          <button class="dlp-alert-btn" id="dlp-dismiss-btn">Understood</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    const dismissBtn = overlay.querySelector('#dlp-dismiss-btn');
    if (dismissBtn) {
      dismissBtn.focus();
      dismissBtn.addEventListener('click', () => overlay.remove());
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
  }

  // Synchronous inspection helper
  function checkViolation(file) {
    if (!file) return null;
    return DLP_RULES.checkFilenamePolicy(file.name);
  }

  // Deep binary check for renamed files (e.g. .fbx or .exe renamed to .png)
  function checkDisguisedPayload(file, onViolation) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function () {
      const spoofViolation = DLP_RULES.inspectBinaryPayload(file.name, reader.result);
      if (spoofViolation) {
        onViolation(spoofViolation);
      }
    };
    reader.readAsArrayBuffer(file.slice(0, 32));
  }

  /**
   * Validates files on an input element.
   * If a violation is found, it clears the input and cancels all events synchronously!
   */
  function inspectAndCleanFileInput(input, event) {
    if (!input || !input.files || input.files.length === 0) return true;

    for (let i = 0; i < input.files.length; i++) {
      const file = input.files[i];
      const violation = checkViolation(file);
      if (violation) {
        input.value = ''; // Wipe files so Telegram gets 0 files!
        if (event) {
          event.preventDefault();
          event.stopPropagation();
          event.stopImmediatePropagation();
        }
        showDLPAlert(file.name, violation);
        return false;
      }

      // Check for disguised files
      checkDisguisedPayload(file, (spoofViolation) => {
        input.value = '';
        showDLPAlert(file.name, spoofViolation);
      });
    }
    return true;
  }

  /**
   * Attaches our security guardian directly to any file input element,
   * including dynamically generated ones created in memory by Telegram.
   */
  function attachGuardianToInput(input) {
    if (!input || input._dlpProtected) return;
    input._dlpProtected = true;

    // Listen on 'change' and 'input' in the capture phase (executes BEFORE Telegram's listeners!)
    const fileHandler = function (e) {
      inspectAndCleanFileInput(input, e);
    };

    input.addEventListener('change', fileHandler, true);
    input.addEventListener('input', fileHandler, true);

    // If Telegram assigns input.onchange = function() {...}, intercept that property too!
    let realOnChange = input.onchange;
    Object.defineProperty(input, 'onchange', {
      configurable: true,
      enumerable: true,
      get: function () {
        return realOnChange;
      },
      set: function (fn) {
        realOnChange = function (e) {
          if (!inspectAndCleanFileInput(input, e)) {
            return false;
          }
          if (typeof fn === 'function') {
            return fn.apply(this, arguments);
          }
        };
      }
    });
  }

  // --- 1. Hook HTMLInputElement.prototype.click (Catches dynamic attachment menus) ---
  // In Telegram Web, clicking "Photo or Video" or "Document" creates a detached <input>
  // and calls input.click(). We hook click() to protect it the instant it is clicked!
  const originalClick = HTMLInputElement.prototype.click;
  HTMLInputElement.prototype.click = function () {
    if (this.type === 'file') {
      attachGuardianToInput(this);
    }
    return originalClick.apply(this, arguments);
  };

  // --- 2. Observe DOM mutations for any file inputs added to page ---
  function scanForFileInputs(root) {
    if (!root) return;
    if (root.querySelectorAll) {
      const inputs = root.querySelectorAll('input[type="file"]');
      inputs.forEach(attachGuardianToInput);
    }
  }

  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      for (const node of m.addedNodes) {
        if (node.nodeType === 1) { // ELEMENT_NODE
          if (node.tagName === 'INPUT' && node.type === 'file') {
            attachGuardianToInput(node);
          } else {
            scanForFileInputs(node);
          }
        }
      }
    }
  });

  observer.observe(document.documentElement || document, {
    childList: true,
    subtree: true
  });

  // Scan immediately
  scanForFileInputs(document);

  // --- 3. Global Capture Phase Listeners on window & document ---
  window.addEventListener('change', (e) => {
    const el = (e.composedPath && e.composedPath()[0]) || e.target;
    if (el && el.tagName === 'INPUT' && el.type === 'file') {
      inspectAndCleanFileInput(el, e);
    }
  }, true);

  // --- 4. Intercept Drag & Drop synchronously ---
  window.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (!dt || !dt.files || dt.files.length === 0) return;

    for (const file of dt.files) {
      const violation = checkViolation(file);
      if (violation) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        showDLPAlert(file.name, violation);
        return false;
      }

      checkDisguisedPayload(file, (spoofViolation) => {
        showDLPAlert(file.name, spoofViolation);
      });
    }
  }, true);

  // --- 5. Intercept Clipboard Paste synchronously ---
  window.addEventListener('paste', (e) => {
    const cd = e.clipboardData;
    if (!cd || !cd.files || cd.files.length === 0) return;

    for (const file of cd.files) {
      const violation = checkViolation(file);
      if (violation) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        showDLPAlert(file.name, violation);
        return false;
      }

      checkDisguisedPayload(file, (spoofViolation) => {
        showDLPAlert(file.name, spoofViolation);
      });
    }
  }, true);

})();
