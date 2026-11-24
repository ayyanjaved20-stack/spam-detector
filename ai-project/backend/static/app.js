(() => {
  const $ = (id) => document.getElementById(id);
  const messageEl = $('message');
  const sourceButtons = Array.from(document.querySelectorAll('.tab'));
  const scanSteps = Array.from(document.querySelectorAll('.scan-step'));
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  let source = 'sms';
  let threshold = 0.6;
  let modelInfo = null;
  let hasResult = false;
  let lastFocused = null;

  /* ---------- Shared helpers ---------- */
  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const setSource = (next) => {
    source = next;
    sourceButtons.forEach((button) => {
      const active = button.dataset.source === next;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    messageEl.placeholder = next === 'sms'
      ? 'Paste an SMS here…'
      : 'Paste email headers and body here…';
  };
  sourceButtons.forEach((button) => button.addEventListener('click', () => setSource(button.dataset.source)));
  setSource('sms');

  messageEl.addEventListener('input', () => {
    $('charCount').textContent = `${messageEl.value.length} CHARACTERS`;
  });
  $('clearBtn').addEventListener('click', () => {
    messageEl.value = '';
    messageEl.dispatchEvent(new Event('input'));
    messageEl.focus();
  });

  const showError = (message) => {
    $('error').textContent = message;
    $('error').hidden = false;
  };

  /* ---------- Drag and drop ---------- */
  const textareaWrap = $('textareaWrap');
  ['dragenter', 'dragover'].forEach((event) => textareaWrap.addEventListener(event, (e) => {
    e.preventDefault();
    textareaWrap.classList.add('dragging');
  }));
  ['dragleave', 'drop'].forEach((event) => textareaWrap.addEventListener(event, (e) => {
    e.preventDefault();
    textareaWrap.classList.remove('dragging');
  }));
  textareaWrap.addEventListener('drop', async (e) => {
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (!file) return;
    if (!/\.(txt|eml|csv|md)$/i.test(file.name)) {
      showError('UNSUPPORTED FILE — use .txt, .eml, .csv or .md.');
      return;
    }
    try {
      messageEl.value = await file.text();
      messageEl.dispatchEvent(new Event('input'));
      messageEl.focus();
      $('error').hidden = true;
    } catch {
      showError('COULD NOT READ THAT FILE.');
    }
  });

  /* ---------- Scan history ---------- */
  const historyKey = 'spamshield_history_v1';
  const loadHistory = () => {
    try {
      return JSON.parse(localStorage.getItem(historyKey)) || [];
    } catch {
      return [];
    }
  };
  const saveHistory = (items) => {
    localStorage.setItem(historyKey, JSON.stringify(items.slice(0, 5)));
  };
  const renderHistory = () => {
    const items = loadHistory();
    const list = $('historyList');
    list.replaceChildren();
    $('historyEmpty').hidden = items.length > 0;

    items.forEach((item, index) => {
      const button = make('button');
      button.type = 'button';
      button.className = 'history-btn';
      const badge = make('span', `mini-badge ${item.label === 'spam' ? 'spam' : 'ham'}`, item.label.toUpperCase());
      const body = make('span');
      body.append(
        make('span', 'history-text', item.text.length > 46 ? `${item.text.slice(0, 46)}…` : item.text),
        make('span', 'history-time', `${item.source.toUpperCase()} · ${item.time}`)
      );
      button.append(badge, body);
      button.addEventListener('click', () => {
        messageEl.value = item.text;
        setSource(item.source);
        messageEl.dispatchEvent(new Event('input'));
        messageEl.focus();

        if (item.result && typeof item.result === 'object') {
          renderResult(item.result, { record: false });
        } else {
          // Older history entries have no cached analysis — re-run, then cache it in place.
          runScan({ record: false, updateIndex: index });
        }
      });
      list.append(make('li', '', ''));
      list.lastChild.append(button);
    });
  };
  renderHistory();

  $('clearHistory').addEventListener('click', () => {
    saveHistory([]);
    renderHistory();
  });

  /* ---------- Result rendering ---------- */
  const updateMeter = (probability, limit) => {
    const pct = Math.max(0, Math.min(100, probability * 100));
    const limitPct = Math.max(0, Math.min(100, limit * 100));
    $('confidenceBar').style.width = `${pct}%`;
    $('confidenceBar').classList.toggle('spam', probability >= limit);
    $('thresholdMarker').style.left = `${limitPct}%`;
    $('thresholdLabel').textContent = `T ${limit.toFixed(2)}`;
    $('meterDanger').style.left = `${limitPct}%`;
    $('meter').setAttribute(
      'aria-label',
      `Spam probability ${Math.round(pct)} percent. Decision threshold ${Math.round(limitPct)} percent.`
    );
  };

  const renderResult = (data, { record = true, updateIndex = null } = {}) => {
    const isSpam = data.label === 'spam';
    hasResult = true;
    $('empty').hidden = true;
    $('scanning').hidden = true;
    $('result').hidden = false;

    const verdict = $('verdict');
    verdict.textContent = isSpam ? 'SPAM' : 'HAM';
    verdict.classList.toggle('spam', isSpam);

    const probability = $('probability');
    probability.textContent = `${Math.round(data.spam_probability * 100)}%`;
    probability.classList.toggle('spam', isSpam);
    $('confidenceValue').textContent = `CONFIDENCE ${Math.round(data.confidence * 100)}%`;

    if (typeof data.threshold === 'number') threshold = data.threshold;
    updateMeter(data.spam_probability, threshold);

    const terms = Array.isArray(data.term_scores) && data.term_scores.length
      ? data.term_scores.map((item) => ({
          term: typeof item === 'string' ? item : item.term,
          score: typeof item === 'string' ? null : item.score,
        }))
      : (data.top_terms || []).map((term) => ({ term, score: null }));

    const chips = $('chips');
    chips.replaceChildren();
    terms.forEach(({ term, score }) => {
      const isSpamTerm = score === null || Number(score) > 0;
      const chip = make('span', `chip ${isSpamTerm ? 'pos' : 'neg'}`, `${isSpamTerm ? '+' : '−'} ${term}`);
      if (score !== null) {
        const value = Number(score);
        chip.title = `Model contribution: ${value >= 0 ? '+' : ''}${value.toFixed(4)}`;
      }
      chips.append(chip);
    });
    $('signalCount').textContent = `${terms.length} TERM${terms.length === 1 ? '' : 'S'}`;
    $('noSignals').hidden = terms.length > 0;

    $('tip').textContent = isSpam
      ? 'Do not click links or share OTP, CNIC or payment details. Verify through an official channel.'
      : 'Looks legitimate, but verify the sender if unexpected. Decision support, not a guarantee.';

    if (record) {
      const items = loadHistory();
      items.unshift({
        text: messageEl.value.trim(),
        source,
        label: data.label,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        result: data,
      });
      saveHistory(items);
      renderHistory();
    } else if (updateIndex !== null) {
      const items = loadHistory();
      if (items[updateIndex]) {
        items[updateIndex].result = data;
        saveHistory(items);
        renderHistory();
      }
    }
  };

  /* ---------- Scan flow ---------- */
  const showScanning = () => {
    $('empty').hidden = true;
    $('result').hidden = true;
    $('scanning').hidden = false;
    scanSteps.forEach((step) => { step.className = 'scan-step'; });
    if (prefersReducedMotion) return;
    scanSteps.forEach((step, index) => {
      setTimeout(() => {
        if ($('scanning').hidden) return;
        step.classList.add('active');
        if (index > 0) scanSteps[index - 1].classList.replace('active', 'done');
      }, index * 190);
    });
  };

  const hideScanning = () => { $('scanning').hidden = true; };

  const restoreState = () => {
    hideScanning();
    $('empty').hidden = hasResult;
    $('result').hidden = !hasResult;
  };

  async function runScan({ record = true, updateIndex = null } = {}) {
    const text = messageEl.value.trim();
    if (!text) {
      showError('INPUT EMPTY — paste a message first.');
      return;
    }

    const button = $('analyzeBtn');
    button.disabled = true;
    button.querySelector('.scan-label').textContent = 'SCANNING…';
    $('error').hidden = true;
    showScanning();

    const request = fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, source }),
    }).then(async (response) => {
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${response.status})`);
      }
      return response.json();
    });

    try {
      const [data] = await (prefersReducedMotion
        ? Promise.all([request])
        : Promise.all([request, wait(620)]));
      renderResult(data, { record, updateIndex });
    } catch (error) {
      restoreState();
      showError(error.message || 'BACKEND OFFLINE — start the backend and retry.');
    } finally {
      button.disabled = false;
      button.querySelector('.scan-label').textContent = 'RUN SCAN';
    }
  }

  $('analyzeBtn').addEventListener('click', () => runScan());
  messageEl.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runScan();
    }
  });

  /* ---------- Model card drawer ---------- */
  const drawer = $('drawer');
  const backdrop = $('drawerBackdrop');

  const renderMatrix = (info) => {
    const host = $('matrix');
    host.replaceChildren();
    const matrix = info && info.confusion_matrix;
    if (!matrix) {
      host.append(make('p', 'rail-muted', 'No metrics yet — run train.py.'));
      return;
    }
    const max = Math.max(...matrix.values.flat(), 1);
    host.append(
      make('div', 'matrix-cell matrix-head'),
      make('div', 'matrix-cell matrix-head', 'PRED HAM'),
      make('div', 'matrix-cell matrix-head', 'PRED SPAM')
    );
    matrix.values.forEach((row, rowIndex) => {
      host.append(make('div', 'matrix-cell matrix-rowhead', `ACTUAL ${matrix.labels[rowIndex].toUpperCase()}`));
      row.forEach((value, columnIndex) => {
        const cell = make('div', `matrix-cell matrix-value${rowIndex === columnIndex ? '' : ' miss'}`, String(value));
        cell.style.setProperty('--heat', (0.05 + 0.28 * value / max).toFixed(3));
        host.append(cell);
      });
    });
  };

  const renderSourceBars = (info) => {
    const host = $('sourceBars');
    host.replaceChildren();
    const sources = (info && info.per_source) || {};
    const entries = Object.entries(sources);
    if (!entries.length) {
      host.append(make('p', 'rail-muted', 'No per-source results yet.'));
      return;
    }
    entries.forEach(([name, detail]) => {
      const row = make('div', 'source-row');
      const head = make('div', 'source-row-head');
      head.append(
        make('span', '', name.toUpperCase()),
        make('span', '', `${(detail.accuracy * 100).toFixed(1)}% · n=${detail.n}`)
      );
      const track = make('div', 'source-track');
      const fill = make('div', 'source-fill');
      fill.style.width = `${detail.accuracy * 100}%`;
      track.append(fill);
      row.append(head, track);
      host.append(row);
    });
  };

  const openDrawer = () => {
    lastFocused = document.activeElement;
    renderMatrix(modelInfo);
    renderSourceBars(modelInfo);
    if (modelInfo && typeof modelInfo.threshold === 'number') {
      $('drawerThreshold').textContent = `Threshold ${modelInfo.threshold.toFixed(2)} + explainable ham-cue guardrail.`;
    }
    drawer.hidden = false;
    backdrop.hidden = false;
    document.body.classList.add('drawer-open');
    $('drawerClose').focus();
  };

  const closeDrawer = () => {
    drawer.hidden = true;
    backdrop.hidden = true;
    document.body.classList.remove('drawer-open');
    if (lastFocused) lastFocused.focus();
  };

  $('aboutBtn').addEventListener('click', openDrawer);
  $('drawerClose').addEventListener('click', closeDrawer);
  backdrop.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !drawer.hidden) closeDrawer();
  });

  /* ---------- Footer metrics ---------- */
  const loadMetrics = async () => {
    try {
      const response = await fetch('/model-info');
      const info = await response.json();
      modelInfo = info;
      if (typeof info.threshold === 'number') threshold = info.threshold;
      $('mStatus').textContent = info.trained ? 'READY' : 'NO MODEL';
      $('mAccuracy').textContent = info.trained ? `${(info.accuracy * 100).toFixed(1)}%` : '—';
      $('mF1').textContent = info.trained ? info.spam_f1.toFixed(2) : '—';
      $('mRows').textContent = info.trained ? info.rows_total.toLocaleString() : '—';
      $('mSources').textContent = info.trained
        ? `${info.sources.sms || 0}S/${info.sources.email || 0}E`
        : '—';
      if (info.trained && typeof info.threshold === 'number') {
        $('drawerThreshold').textContent = `Threshold ${info.threshold.toFixed(2)} + explainable ham-cue guardrail.`;
      }
    } catch {
      $('mStatus').textContent = 'OFFLINE';
    }
  };
  loadMetrics();
})();
