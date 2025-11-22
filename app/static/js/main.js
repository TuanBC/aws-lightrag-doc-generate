/**
 * Client-side JavaScript for address validation and UX improvements.
 */

(function() {
  'use strict';

  const ADDRESS_LENGTH = 42;
  const HEX_PATTERN = /^[0-9a-fA-F]+$/;

  /**
   * Normalize and validate Ethereum address input.
   */
  function normalizeAddress(input) {
    let value = input.value.trim();
    
    // Auto-prefix with 0x if missing
    if (!value.startsWith('0x') && value.length > 0) {
      value = '0x' + value;
    }
    
    // Remove 0x for validation, then add back
    const hexPart = value.startsWith('0x') ? value.slice(2) : value;
    
    // Validate hex characters
    if (hexPart.length > 0 && !HEX_PATTERN.test(hexPart)) {
      return { valid: false, normalized: value, error: 'Invalid hex characters' };
    }
    
    // Check length
    if (value.length > ADDRESS_LENGTH) {
      return { valid: false, normalized: value, error: 'Address too long' };
    }
    
    if (value.length < 2) {
      return { valid: false, normalized: value, error: null };
    }
    
    if (value.length < ADDRESS_LENGTH) {
      return { valid: false, normalized: value, error: 'Address incomplete' };
    }
    
    return { valid: true, normalized: value.toLowerCase(), error: null };
  }

  /**
   * Update input field with normalized value and show feedback.
   */
  function updateAddressInput(input, feedbackEl) {
    const result = normalizeAddress(input);
    input.value = result.normalized;
    
    if (feedbackEl) {
      if (result.error) {
        feedbackEl.textContent = result.error;
        feedbackEl.style.display = 'block';
        feedbackEl.classList.add('error');
      } else if (result.valid) {
        feedbackEl.textContent = '✓ Valid address';
        feedbackEl.style.display = 'block';
        feedbackEl.classList.remove('error');
        feedbackEl.classList.add('success');
      } else {
        feedbackEl.style.display = 'none';
        feedbackEl.classList.remove('error', 'success');
      }
    }
    
    return result.valid;
  }

  /**
   * Show loading state on form submission.
   */
  function setFormLoading(form, isLoading) {
    const submitBtn = form.querySelector('button[type="submit"]');
    const input = form.querySelector('input[name="wallet_address"]');
    
    if (isLoading) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Analyzing...';
      // Don't disable input - it needs to be submitted with the form
      input.readOnly = true;
      form.classList.add('loading');
    } else {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Check Score';
      input.readOnly = false;
      form.classList.remove('loading');
    }
  }

  /**
   * Initialize form handlers.
   */
  function initAddressForm() {
    const form = document.querySelector('.address-form');
    if (!form) return;

    const input = form.querySelector('input[name="wallet_address"]');
    const feedbackEl = form.querySelector('.feedback') || createFeedbackElement(form);
    
    // Real-time validation on input
    input.addEventListener('input', function() {
      updateAddressInput(input, feedbackEl);
    });
    
    // Validate on blur
    input.addEventListener('blur', function() {
      updateAddressInput(input, feedbackEl);
    });
    
    // Handle form submission
    form.addEventListener('submit', function(e) {
      // Ensure the input has the full address including 0x
      const result = normalizeAddress(input);
      
      if (!result.valid) {
        e.preventDefault();
        if (feedbackEl) {
          feedbackEl.textContent = result.error || 'Please enter a valid 42-character Ethereum address';
          feedbackEl.style.display = 'block';
          feedbackEl.classList.add('error');
        }
        input.focus();
        return false;
      }
      
      // Ensure the normalized address is in the input before submission
      // This must happen before setting loading state
      input.value = result.normalized;
      
      // Small delay to ensure value is set, then set loading state
      setTimeout(function() {
        setFormLoading(form, true);
      }, 10);
      
      // Don't prevent default - allow form to submit normally
      // The form will navigate/reload, so loading state is just visual feedback
    });
    
    // Paste handler - auto-normalize pasted addresses
    input.addEventListener('paste', function(e) {
      setTimeout(() => {
        updateAddressInput(input, feedbackEl);
      }, 10);
    });
  }

  /**
   * Create feedback element if it doesn't exist.
   */
  function createFeedbackElement(form) {
    const feedback = document.createElement('p');
    feedback.className = 'feedback';
    feedback.style.display = 'none';
    form.appendChild(feedback);
    return feedback;
  }

  /**
   * Copy address to clipboard.
   */
  function initCopyButtons() {
    document.addEventListener('click', function(e) {
      if (e.target.classList.contains('copy-address')) {
        const address = e.target.dataset.address;
        if (address) {
          navigator.clipboard.writeText(address).then(() => {
            const originalText = e.target.textContent;
            e.target.textContent = 'Copied!';
            setTimeout(() => {
              e.target.textContent = originalText;
            }, 2000);
          }).catch(() => {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = address;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
          });
        }
      }
    });
  }

  /**
   * Initialize all features when DOM is ready.
   */
  function init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
      return;
    }
    
    initAddressForm();
    initCopyButtons();
  }

  // Start initialization
  init();
})();

