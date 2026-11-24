// Wrapping everything in an IIFE keeps helper names out of the global page scope.
// Open an immediately invoked function that runs once when the script loads.
(() => {
  // Define a short helper that looks up an element by its id.
  const $ = (id) => document.getElementById(id);
  // Cache the message textarea because many handlers use it.
  const messageEl = $('message');
  // Collect the SMS and email tab buttons into an array for iteration.
  const sourceButtons = Array.from(document.querySelectorAll('.tab'));
  // Collect the three animated scan step elements for progress display.
  const scanSteps = Array.from(document.querySelectorAll('.scan-step'));
  // Respect the operating system setting that asks for less animation.
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Define a promise-based delay used to show the scanning animation briefly.
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
// (blank line separates logical blocks)

  // Start with SMS as the selected message source.
  let source = 'sms';
  // Start with a local threshold until the backend reports the trained value.
  let threshold = 0.6;
  // Hold the latest model metrics here once they arrive.
  let modelInfo = null;
  // Track whether a result is currently visible for state restoration.
  let hasResult = false;
  // Remember which element had focus before a dialog opened.
  let lastFocused = null;
// (blank line separates logical blocks)

  // Note for readers: small DOM building helpers shared by all renderers.
  /* ---------- Shared helpers ---------- */
  // Define a factory that creates an element with an optional class and text.
  const make = (tag, className, text) => {
    // Create the element with the requested tag name.
    const node = document.createElement(tag);
    // Apply a CSS class only when one was supplied.
    if (className) node.className = className;
    // Set plain text content only when text was supplied.
    if (text !== undefined) node.textContent = text;
    // Hand the finished node back to the caller.
    return node;
  // Close the element factory.
  };
// (blank line separates logical blocks)

  // Define the function that switches between SMS and email input modes.
  const setSource = (next) => {
    // Store the newly selected source in shared state.
    source = next;
    // Visit every tab button to update its visual and accessible state.
    sourceButtons.forEach((button) => {
      // Work out whether this button represents the selected source.
      const active = button.dataset.source === next;
      // Toggle the active styling class to match that decision.
      button.classList.toggle('active', active);
      // aria-pressed tells screen readers which tab is currently selected.
      // Expose the same state through an accessibility attribute as a string.
      button.setAttribute('aria-pressed', String(active));
    // Close the button loop.
    });
    // The placeholder is updated so students know what format to paste.
    // Start a ternary that chooses the placeholder for the new source.
    messageEl.placeholder = next === 'sms'
      // Offer the SMS hint when SMS is selected.
      ? 'Paste an SMS here…'
      // Offer the email hint when email is selected.
      : 'Paste email headers and body here…';
  // Close the assignment and the function.
  };
  // Wire every tab button to switch source when clicked.
  sourceButtons.forEach((button) => button.addEventListener('click', () => setSource(button.dataset.source)));
  // Initialise the tabs and placeholder for SMS on page load.
  setSource('sms');
// (blank line separates logical blocks)

  // Recompute the character counter whenever the user types.
  messageEl.addEventListener('input', () => {
    // Show the current length with a monospace-friendly uppercase suffix.
    $('charCount').textContent = `${messageEl.value.length} CHARACTERS`;
  // Close the input listener.
  });
  // Handle the clear button click.
  $('clearBtn').addEventListener('click', () => {
    // Empty the textarea.
    messageEl.value = '';
    // Fire a synthetic input event so the character counter updates too.
    messageEl.dispatchEvent(new Event('input'));
    // Return focus to the textarea for fast re-entry.
    messageEl.focus();
  // Close the clear button listener.
  });
// (blank line separates logical blocks)

  // Define a helper that reveals an error message in the reserved paragraph.
  const showError = (message) => {
    // Write the message text into the error element.
    $('error').textContent = message;
    // Make the previously hidden error element visible.
    $('error').hidden = false;
  // Close the error helper.
  };
// (blank line separates logical blocks)

  // Note for readers: file drop support lets a student load a saved message.
  /* ---------- Drag and drop ---------- */
  // Cache the textarea wrapper that receives drag events.
  const textareaWrap = $('textareaWrap');
  // Highlight the wrapper while a file is dragged over it.
  ['dragenter', 'dragover'].forEach((event) => textareaWrap.addEventListener(event, (e) => {
    // Prevent the browser from opening the file as a navigation.
    e.preventDefault();
    // Add the dragging class so CSS reveals the drop hint.
    textareaWrap.classList.add('dragging');
  // Close the drag enter and over listeners.
  }));
  // Clear the highlight when the file leaves or the drop completes.
  ['dragleave', 'drop'].forEach((event) => textareaWrap.addEventListener(event, (e) => {
    // Prevent default browser handling for these events as well.
    e.preventDefault();
    // Remove the dragging class so the hint disappears.
    textareaWrap.classList.remove('dragging');
  // Close the drag leave and drop listeners.
  }));
  // Handle a real file drop asynchronously.
  textareaWrap.addEventListener('drop', async (e) => {
    // Pull the first file out of the browser data transfer object.
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    // Do nothing when the drop did not contain a file.
    if (!file) return;
    // Reject unsupported extensions with a clear message.
    if (!/\.(txt|eml|csv|md)$/i.test(file.name)) {
      // Show that error to the user.
      showError('UNSUPPORTED FILE — use .txt, .eml, .csv or .md.');
      // Stop processing an unsupported file.
      return;
    // Close the extension check.
    }
    // Reading starts only after the type check, and errors are surfaced in the UI.
    // Start a guarded file read.
    try {
      // Load the file contents as text into the textarea.
      messageEl.value = await file.text();
      // Refresh the character counter with a synthetic input event.
      messageEl.dispatchEvent(new Event('input'));
      // Focus the textarea so the pasted content can be edited.
      messageEl.focus();
      // Hide any previous error now that the load succeeded.
      $('error').hidden = true;
    // Handle unreadable files with a generic message.
    } catch {
      // Close the guarded read and the drop handler.
      showError('COULD NOT READ THAT FILE.');
    // Execute } as part of the browser interaction.
    }
  // Note for readers: the scan history is stored in browser localStorage.
  });
// (blank line separates logical blocks)

  // Define a helper that reads saved history safely.
  /* ---------- Scan history ---------- */
  // Start a guarded parse because stored JSON may be corrupt.
  const historyKey = 'spamshield_history_v1';
  // Parse the stored JSON or use an empty list when nothing is saved.
  const loadHistory = () => {
    // Handle malformed stored data by returning an empty history.
    try {
      // Close the catch block.
      return JSON.parse(localStorage.getItem(historyKey)) || [];
    // Close the load helper.
    } catch {
      // Define a helper that writes history back to the browser.
      return [];
    // Only five newest scans are kept so localStorage stays small and the UI uncluttered.
    // Serialise and save at most the first five entries.
    }
  // Close the save helper.
  };
  // Define the function that rebuilds the history list from storage.
  const saveHistory = (items) => {
    // Read the current history entries.
    localStorage.setItem(historyKey, JSON.stringify(items.slice(0, 5)));
  // Cache the list element that will hold the buttons.
  };
  // Remove previously rendered list items before redrawing.
  const renderHistory = () => {
    // Toggle the empty message based on whether entries exist.
    const items = loadHistory();
    // Declare a named value used by the browser-side logic.
    const list = $('historyList');
    // Render each history entry with its index for later updates.
    list.replaceChildren();
    // Create a button that restores a past scan.
    $('historyEmpty').hidden = items.length > 0;
// (blank line separates logical blocks)

    // Apply the history button styling class.
    items.forEach((item, index) => {
      // A mini badge shows the earlier verdict at a glance.
      // Build a coloured badge from the stored label and uppercase text.
      const button = make('button');
      // Create a container for the preview text and timestamp.
      button.type = 'button';
      // Appending child nodes avoids injecting stored text as HTML.
      // Start adding the preview and time spans to the container.
      button.className = 'history-btn';
      // Show a truncated message preview so rows stay compact.
      const badge = make('span', `mini-badge ${item.label === 'spam' ? 'spam' : 'ham'}`, item.label.toUpperCase());
      // Show the source and a short time stamp on a second line.
      const body = make('span');
      // Close the append call.
      body.append(
        // Put the badge and text container inside the button.
        make('span', 'history-text', item.text.length > 46 ? `${item.text.slice(0, 46)}…` : item.text),
        // Clicking history restores the exact message and mode from that past scan.
        // Define the click handler that reopens a stored scan.
        make('span', 'history-time', `${item.source.toUpperCase()} · ${item.time}`)
      // Put the saved message text back into the textarea.
      );
      // Switch the SMS or email tabs back to the saved mode.
      button.append(badge, body);
      // Update the character counter for the restored text.
      button.addEventListener('click', () => {
        // Focus the textarea so the student can edit before rescanning.
        messageEl.value = item.text;
        // Execute setSource(item.source); as part of the browser interaction.
        setSource(item.source);
        // Cached result objects avoid an unnecessary network call and keep the old verdict visible.
        // Use the cached result immediately when one was stored.
        messageEl.dispatchEvent(new Event('input'));
        // Render that result without adding a new history row.
        messageEl.focus();
// (blank line separates logical blocks)

        // updateIndex replaces the old entry in place rather than duplicating it.
        // Run a scan that patches this specific history slot when finished.
        if (item.result && typeof item.result === 'object') {
          // Close the conditional and the click handler.
          renderResult(item.result, { record: false });
        // Create a list item wrapper for safe structural markup.
        } else {
          // Insert the button inside that list item.
          // Older history entries have no cached analysis — re-run, then cache it in place.
          // Close the history entry loop and renderer.
          runScan({ record: false, updateIndex: index });
        // Draw the stored history on initial page load.
        }
      // Execute }); as part of the browser interaction.
      });
      // Wire the purge button to clear storage and redraw the empty state.
      list.append(make('li', '', ''));
      // Save an empty history list.
      list.lastChild.append(button);
    // Rebuild the list so the empty message appears.
    });
  // Close the purge handler.
  };
  // Execute renderHistory(); as part of the browser interaction.
  renderHistory();
// (blank line separates logical blocks)

  // Define a helper that moves the probability meter and its threshold marker.
  $('clearHistory').addEventListener('click', () => {
    // Clamp the probability to a percentage between zero and one hundred.
    saveHistory([]);
    // Clamp the threshold to the same percentage scale.
    renderHistory();
  // Set the filled bar width to the spam probability.
  });
// (blank line separates logical blocks)

  // Place the threshold marker at the matching position.
  /* ---------- Result rendering ---------- */
  // Print the threshold value next to the marker.
  const updateMeter = (probability, limit) => {
    // Shade the danger zone starting at the threshold.
    const pct = Math.max(0, Math.min(100, probability * 100));
    // A descriptive aria-label makes the visual meter understandable without sight.
    // Start setting an accessible label on the meter.
    const limitPct = Math.max(0, Math.min(100, limit * 100));
    // Supply the label naming both probability and threshold.
    $('confidenceBar').style.width = `${pct}%`;
    // Close the setAttribute call.
    $('confidenceBar').classList.toggle('spam', probability >= limit);
    // Close the meter helper.
    $('thresholdMarker').style.left = `${limitPct}%`;
    // Connect a DOM element or event to its handler.
    $('thresholdLabel').textContent = `T ${limit.toFixed(2)}`;
    // Define the renderer for a prediction response.
    $('meterDanger').style.left = `${limitPct}%`;
    // Allow the caller to disable history recording or patch an existing entry.
    $('meter').setAttribute(
      // Work out from the label which verdict styling to use.
      'aria-label',
      // Remember that a result is now visible for later state restoration.
      `Spam probability ${Math.round(pct)} percent. Decision threshold ${Math.round(limitPct)} percent.`
    // Hide the waiting placeholder.
    );
  // Hide the scanning animation.
  };
// (blank line separates logical blocks)

  // Declare a named value used by the browser-side logic.
  const renderResult = (data, { record = true, updateIndex = null } = {}) => {
    // Cache the verdict element.
    const isSpam = data.label === 'spam';
    // Write SPAM or HAM into it.
    hasResult = true;
    // Colour the verdict red only for spam.
    $('empty').hidden = true;
    // Connect a DOM element or event to its handler.
    $('scanning').hidden = true;
    // Cache the score element.
    $('result').hidden = false;
// (blank line separates logical blocks)

    // Colour the score red only for spam.
    const verdict = $('verdict');
    // Show the model's confidence beside the score.
    verdict.textContent = isSpam ? 'SPAM' : 'HAM';
    // Execute verdict.classList.toggle('spam', isSpam); as part of the browser interaction.
    verdict.classList.toggle('spam', isSpam);
// (blank line separates logical blocks)

    // Move the meter using the current probability and threshold.
    const probability = $('probability');
    // Execute probability.textContent = `${Math.round(data.spam_probability * 100)}%`; as part of the browser interaction.
    probability.textContent = `${Math.round(data.spam_probability * 100)}%`;
    // Prefer signed term contributions when available, otherwise fall back to top terms.
    // Normalising both shapes into one list keeps the chip renderer simple.
    // Check whether the response contains an array of scored terms.
    probability.classList.toggle('spam', isSpam);
    // Map each scored term into a uniform object.
    $('confidenceValue').textContent = `CONFIDENCE ${Math.round(data.confidence * 100)}%`;
// (blank line separates logical blocks)

    // Keep the numeric contribution when it exists.
    if (typeof data.threshold === 'number') threshold = data.threshold;
    // Close the scored term mapping.
    updateMeter(data.spam_probability, threshold);
// (blank line separates logical blocks)

    // Close the terms selection.
    const terms = Array.isArray(data.term_scores) && data.term_scores.length
      // Define a callback or helper function used by this page.
      ? data.term_scores.map((item) => ({
          // Cache the chip container.
          term: typeof item === 'string' ? item : item.term,
          // Clear chips from any previous scan.
          score: typeof item === 'string' ? null : item.score,
        // Render one chip per detected term.
        }))
      // Treat a missing score or a positive score as spam-leaning.
      : (data.top_terms || []).map((term) => ({ term, score: null }));
// Positive contributions are red chips and negative ones are dashed ham-leaning chips.
// (blank line separates logical blocks)

    // Add a tooltip when the backend supplied a numeric contribution.
    const chips = $('chips');
    // Convert the stored score to a number.
    chips.replaceChildren();
    // Show the exact signed contribution to four decimal places.
    terms.forEach(({ term, score }) => {
      // Close the tooltip block.
      const isSpamTerm = score === null || Number(score) > 0;
      // Append the chip to the container.
      const chip = make('span', `chip ${isSpamTerm ? 'pos' : 'neg'}`, `${isSpamTerm ? '+' : '−'} ${term}`);
      // Close the term loop.
      if (score !== null) {
        // Update the signal count with correct singular or plural wording.
        const value = Number(score);
        // Hide the no-signals note when terms were found.
        chip.title = `Model contribution: ${value >= 0 ? '+' : ''}${value.toFixed(4)}`;
      // Execute } as part of the browser interaction.
      }
      // The safety tip is deliberately different for spam and ham results.
      // Start choosing the advice text by verdict.
      chips.append(chip);
    // Warn against clicking links or sharing private data for spam.
    });
    // Advise verifying an unexpected legitimate message instead.
    $('signalCount').textContent = `${terms.length} TERM${terms.length === 1 ? '' : 'S'}`;
    // Close the tip assignment.
    $('noSignals').hidden = terms.length > 0;
// (blank line separates logical blocks)

    // Recording happens only for fresh scans; restored or patched scans avoid duplicates.
    // Handle a brand new scan that should be saved.
    $('tip').textContent = isSpam
      // Read the current history from storage.
      ? 'Do not click links or share OTP, CNIC or payment details. Verify through an official channel.'
      // Put the new entry at the front of the list.
      : 'Looks legitimate, but verify the sender if unexpected. Decision support, not a guarantee.';
// (blank line separates logical blocks)

    // Store the selected source mode.
    if (record) {
      // Store the verdict label.
      const items = loadHistory();
      // Store a short local time stamp.
      items.unshift({
        // Caching the whole response lets history clicks restore the exact result offline.
        // Cache the full prediction result for later reuse.
        text: messageEl.value.trim(),
        // Close the new entry object.
        source,
        // Persist the updated history.
        label: data.label,
        // Redraw the history list.
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        // Handle a rescan of an older history entry instead.
        result: data,
      // Read the history so one slot can be patched.
      });
      // Verify that the requested index still exists.
      saveHistory(items);
      // Replace only the cached result at that index.
      renderHistory();
    // Persist the patched history.
    } else if (updateIndex !== null) {
      // Redraw the history list.
      const items = loadHistory();
      // Close the index guard.
      if (items[updateIndex]) {
        // Close the patch branch and renderer.
        items[updateIndex].result = data;
        // Execute saveHistory(items); as part of the browser interaction.
        saveHistory(items);
        // Note for readers: the scanning animation runs while the network request is pending.
        renderHistory();
      // Define a helper that reveals the scanning stage.
      }
    // Hide the empty placeholder and any old result.
    }
  // Show the scanning panel.
  };
// (blank line separates logical blocks)

  // Stop here when the user prefers reduced motion.
  /* ---------- Scan flow ---------- */
  // Schedule the three steps to light up in sequence.
  const showScanning = () => {
    // Start a timer callback for one step.
    $('empty').hidden = true;
    // Do nothing if scanning was already hidden by a fast response.
    $('result').hidden = true;
    // Mark this step as active.
    $('scanning').hidden = false;
    // Earlier steps become done as the animation advances.
    // Mark the previous step as completed and remove its active state.
    scanSteps.forEach((step) => { step.className = 'scan-step'; });
    // Stagger each step by 190 milliseconds.
    if (prefersReducedMotion) return;
    // Close the timer and step loop.
    scanSteps.forEach((step, index) => {
      // Close the scanning helper.
      setTimeout(() => {
        // Branch the logic based on the current state.
        if ($('scanning').hidden) return;
        // Define a tiny helper that hides the scanning stage.
        step.classList.add('active');
        // Branch the logic based on the current state.
        if (index > 0) scanSteps[index - 1].classList.replace('active', 'done');
      // Define a helper that restores the correct panel after a failed scan.
      }, index * 190);
    // Hide the scanning stage.
    });
  // Show the placeholder when there is no result to return to.
  };
// (blank line separates logical blocks)

  // Close the state restoration helper.
  const hideScanning = () => { $('scanning').hidden = true; };
// (blank line separates logical blocks)

  // This function owns the whole scan lifecycle including loading, error and reset states.
  // Define the async scan function with optional history behaviour.
  const restoreState = () => {
    // Read and trim the message text before any request is made.
    hideScanning();
    // Stop with an inline error when the input is empty.
    $('empty').hidden = hasResult;
    // Report the empty input error.
    $('result').hidden = !hasResult;
  // Leave the function without calling the backend.
  };
// (blank line separates logical blocks)

  // Execute async function runScan({ record = true, updateIndex = null } = {}) { as part of the browser interaction.
  async function runScan({ record = true, updateIndex = null } = {}) {
    // Cache the scan button so it can be disabled during the request.
    const text = messageEl.value.trim();
    // Disable the button to prevent duplicate submissions.
    if (!text) {
      // Change the button label to show progress.
      showError('INPUT EMPTY — paste a message first.');
      // Clear any previous error message.
      return;
    // Show the animated scan steps.
    }
// (blank line separates logical blocks)

    // Fetching starts immediately and returns a promise that later resolves to JSON.
    // Start a POST request to the prediction endpoint.
    const button = $('analyzeBtn');
    // Declare the JSON method explicitly.
    button.disabled = true;
    // Tell the server the body is JSON.
    button.querySelector('.scan-label').textContent = 'SCANNING…';
    // Send the message text and selected source as JSON.
    $('error').hidden = true;
    // Begin handling the HTTP response.
    showScanning();
// Checking response.ok converts HTTP failures into thrown errors caught below.
// (blank line separates logical blocks)

    // Try to read the server's error detail, defaulting to an empty object.
    const request = fetch('/predict', {
      // Throw an error using server detail or the status code.
      method: 'POST',
      // Return parsed JSON for a successful response.
      headers: { 'Content-Type': 'application/json' },
      // Close the response handler and request definition.
      body: JSON.stringify({ text, source }),
    // Define a callback or helper function used by this page.
    }).then(async (response) => {
      // Start the guarded wait for the request result.
      if (!response.ok) {
        // Reduced-motion users skip the 620 millisecond animation delay entirely.
        // Wait only for the request when animation is disabled.
        const detail = await response.json().catch(() => ({}));
        // Otherwise wait for both the request and the minimum animation time.
        throw new Error(detail.detail || `Request failed (${response.status})`);
      // Unpack the response data from the awaited promise.
      }
      // Render the prediction with the caller's history options.
      return response.json();
    // Handle any network or server error.
    });
// (blank line separates logical blocks)

    // Display the error text or a backend-offline fallback.
    try {
      // Reset the button regardless of success or failure.
      const [data] = await (prefersReducedMotion
        // Re-enable the button for another scan.
        ? Promise.all([request])
        // Restore the normal button label.
        : Promise.all([request, wait(620)]));
      // Close the try, catch and finally block.
      renderResult(data, { record, updateIndex });
    // Close the scan function.
    } catch (error) {
      // Execute restoreState(); as part of the browser interaction.
      restoreState();
      // Run a fresh scan when the analyse button is clicked.
      showError(error.message || 'BACKEND OFFLINE — start the backend and retry.');
    // Support Control+Enter or Command+Enter as a keyboard shortcut.
    } finally {
      // Detect the modifier plus Enter key combination.
      button.disabled = false;
      // Stop the browser's default action for that shortcut.
      button.querySelector('.scan-label').textContent = 'RUN SCAN';
    // Start the same scan routine.
    }
  // Close the key guard and listener.
  }
// (blank line separates logical blocks)

  // Note for readers: the model information drawer uses a dialog pattern.
  $('analyzeBtn').addEventListener('click', () => runScan());
  // Cache the drawer panel element.
  messageEl.addEventListener('keydown', (e) => {
    // Cache the dark backdrop element.
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      // Execute e.preventDefault(); as part of the browser interaction.
      e.preventDefault();
      // Define a helper that draws the confusion matrix from training metrics.
      runScan();
    // Cache the matrix container.
    }
  // Clear any previously drawn matrix cells.
  });
// (blank line separates logical blocks)

  // Show a friendly message and stop when metrics are unavailable.
  /* ---------- Model card drawer ---------- */
  // Print the placeholder message.
  const drawer = $('drawer');
  // Leave the helper early.
  const backdrop = $('drawerBackdrop');
// (blank line separates logical blocks)

  // Scale cell colours relative to the largest count, with a floor of one.
  const renderMatrix = (info) => {
    // The header row is built as three grid cells to match the CSS grid layout.
    // Start appending the header cells.
    const host = $('matrix');
    // Add an empty corner cell.
    host.replaceChildren();
    // Add the predicted ham column heading.
    const matrix = info && info.confusion_matrix;
    // Add the predicted spam column heading.
    if (!matrix) {
      // Close the header append call.
      host.append(make('p', 'rail-muted', 'No metrics yet — run train.py.'));
      // Walk through the matrix rows with their index.
      return;
    // Add a row heading naming the actual class.
    }
    // Walk through each cell value with its column index.
    const max = Math.max(...matrix.values.flat(), 1);
    // Off-diagonal cells are marked as misses so errors stand out visually.
    // Build a styled cell and flag wrong predictions with a miss class.
    host.append(
      // Set a heat variable used by CSS to shade the cell by count.
      make('div', 'matrix-cell matrix-head'),
      // Add the finished cell to the container.
      make('div', 'matrix-cell matrix-head', 'PRED HAM'),
      // Close the value loop and row loop.
      make('div', 'matrix-cell matrix-head', 'PRED SPAM')
    // Close the matrix renderer.
    );
    // Define a callback or helper function used by this page.
    matrix.values.forEach((row, rowIndex) => {
      // Define a helper that draws one bar per data source.
      host.append(make('div', 'matrix-cell matrix-rowhead', `ACTUAL ${matrix.labels[rowIndex].toUpperCase()}`));
      // Cache the per-source bar container.
      row.forEach((value, columnIndex) => {
        // Clear any previous bars.
        const cell = make('div', `matrix-cell matrix-value${rowIndex === columnIndex ? '' : ' miss'}`, String(value));
        // Read the per_source map or use an empty object.
        cell.style.setProperty('--heat', (0.05 + 0.28 * value / max).toFixed(3));
        // Convert the object into key and value pairs.
        host.append(cell);
      // Show a placeholder when no per-source metrics exist.
      });
    // Print that placeholder.
    });
  // Leave the helper early.
  };
// (blank line separates logical blocks)

  // Each row pairs a text heading with a proportional filled track.
  // Render one row per source and its detail object.
  const renderSourceBars = (info) => {
    // Create the row container.
    const host = $('sourceBars');
    // Create the heading container.
    host.replaceChildren();
    // Start adding the source name and its accuracy with sample size.
    const sources = (info && info.per_source) || {};
    // Show the uppercase source name.
    const entries = Object.entries(sources);
    // Show accuracy to one decimal place plus the row count.
    if (!entries.length) {
      // Close the heading append call.
      host.append(make('p', 'rail-muted', 'No per-source results yet.'));
      // Create the empty track element.
      return;
    // Create the coloured fill element.
    }
    // Set the fill width to this source's accuracy percentage.
    entries.forEach(([name, detail]) => {
      // Put the fill inside the track.
      const row = make('div', 'source-row');
      // Put the heading and track inside the row.
      const head = make('div', 'source-row-head');
      // Append the completed row to the container.
      head.append(
        // Close the loop and renderer.
        make('span', '', name.toUpperCase()),
        // Execute make('span', '', `${(detail.accuracy * 100).toFixed(1)}% · n=${detail.n}`) as part of the browser interaction.
        make('span', '', `${(detail.accuracy * 100).toFixed(1)}% · n=${detail.n}`)
      // Define the drawer opening routine.
      );
      // Remembering focus lets keyboard users return to the button when the drawer closes.
      // Save the currently focused element for later restoration.
      const track = make('div', 'source-track');
      // Draw the confusion matrix using cached model info.
      const fill = make('div', 'source-fill');
      // Draw the per-source bars using the same info.
      fill.style.width = `${detail.accuracy * 100}%`;
      // Update the explanatory threshold line when metrics include one.
      track.append(fill);
      // Build that line from the trained threshold and the guardrail note.
      row.append(head, track);
      // Close the conditional.
      host.append(row);
    // Reveal the drawer and its backdrop.
    });
  // Lock page scrolling while the drawer is open.
  };
// (blank line separates logical blocks)

  // Close the opening routine.
  const openDrawer = () => {
    // Execute lastFocused = document.activeElement; as part of the browser interaction.
    lastFocused = document.activeElement;
    // Define the drawer closing routine.
    renderMatrix(modelInfo);
    // Hide the drawer panel.
    renderSourceBars(modelInfo);
    // Hide the backdrop.
    if (modelInfo && typeof modelInfo.threshold === 'number') {
      // Re-enable page scrolling.
      $('drawerThreshold').textContent = `Threshold ${modelInfo.threshold.toFixed(2)} + explainable ham-cue guardrail.`;
    // Focus restoration is the accessibility counterpart of the earlier focus save.
    // Return focus to the element that opened the drawer.
    }
    // Close the closing routine.
    drawer.hidden = false;
    // Execute backdrop.hidden = false; as part of the browser interaction.
    backdrop.hidden = false;
    // Open the drawer from the Model Info button.
    document.body.classList.add('drawer-open');
    // Close it with the visible close button.
    $('drawerClose').focus();
  // Close it by clicking the backdrop.
  };
// (blank line separates logical blocks)

  // Handle the Escape key only while the drawer is open.
  const closeDrawer = () => {
    // Close the key listener.
    drawer.hidden = true;
    // Execute backdrop.hidden = true; as part of the browser interaction.
    backdrop.hidden = true;
    // Note for readers: footer metrics come from the model-info endpoint.
    document.body.classList.remove('drawer-open');
    // Define an async loader for the footer numbers.
    if (lastFocused) lastFocused.focus();
  // Start a guarded request because the backend may be offline.
  };
// (blank line separates logical blocks)

  // Parse the JSON response.
  $('aboutBtn').addEventListener('click', openDrawer);
  // Cache the metrics for the drawer renderers.
  $('drawerClose').addEventListener('click', closeDrawer);
  // Adopt the trained threshold for the probability meter too.
  backdrop.addEventListener('click', closeDrawer);
  // Show READY or NO MODEL in the status cell.
  document.addEventListener('keydown', (e) => {
    // Show accuracy when trained, otherwise a dash.
    if (e.key === 'Escape' && !drawer.hidden) closeDrawer();
  // Show spam F1 when trained, otherwise a dash.
  });
// (blank line separates logical blocks)

  // The sources cell is built across lines but remains one assignment.
  // Start choosing the sources summary text.
  /* ---------- Footer metrics ---------- */
  // Show SMS and email counts in a compact form.
  const loadMetrics = async () => {
    // Show a dash when no model is trained.
    try {
      // Close the sources assignment.
      const response = await fetch('/model-info');
      // Refresh the drawer threshold text when training info is available.
      const info = await response.json();
      // Build the drawer text from the fetched threshold.
      modelInfo = info;
      // Close the conditional.
      if (typeof info.threshold === 'number') threshold = info.threshold;
      // Handle an offline backend by marking the footer as offline.
      $('mStatus').textContent = info.trained ? 'READY' : 'NO MODEL';
      // Close the catch block and loader.
      $('mAccuracy').textContent = info.trained ? `${(info.accuracy * 100).toFixed(1)}%` : '—';
      // Fetch the metrics immediately on page load.
      $('mF1').textContent = info.trained ? info.spam_f1.toFixed(2) : '—';
      // Close the outer IIFE.
      $('mRows').textContent = info.trained ? info.rows_total.toLocaleString() : '—';
      // 
      $('mSources').textContent = info.trained
        // Execute ? `${info.sources.sms || 0}S/${info.sources.email || 0}E` as part of the browser interaction.
        ? `${info.sources.sms || 0}S/${info.sources.email || 0}E`
        // Execute : '—'; as part of the browser interaction.
        : '—';
      // Branch the logic based on the current state.
      if (info.trained && typeof info.threshold === 'number') {
        // Connect a DOM element or event to its handler.
        $('drawerThreshold').textContent = `Threshold ${info.threshold.toFixed(2)} + explainable ham-cue guardrail.`;
      // Execute } as part of the browser interaction.
      }
    // Execute } catch { as part of the browser interaction.
    } catch {
      // Connect a DOM element or event to its handler.
      $('mStatus').textContent = 'OFFLINE';
    // Execute } as part of the browser interaction.
    }
  // Execute }; as part of the browser interaction.
  };
  // Execute loadMetrics(); as part of the browser interaction.
  loadMetrics();
// Execute })(); as part of the browser interaction.
})();
