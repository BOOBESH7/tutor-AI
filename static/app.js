const firebaseVersion = '11.10.0';
let auth = null;
let authMethods = null;
let currentUser = null;
let authDialog = null;
let authReadyResolver;
const authReady = new Promise((resolve) => { authReadyResolver = resolve; });

async function initializeFirebaseAuth() {
  try {
    const configResponse = await fetch('/api/config');
    if (!configResponse.ok) {
      throw new Error(`Firebase config request failed (${configResponse.status}).`);
    }
    const config = await configResponse.json();
    if (!config.apiKey || !config.projectId || !config.appId) {
      authReadyResolver(false);
      return;
    }
    const [appSdk, authSdk] = await Promise.all([
      import(`https://www.gstatic.com/firebasejs/${firebaseVersion}/firebase-app.js`),
      import(`https://www.gstatic.com/firebasejs/${firebaseVersion}/firebase-auth.js`),
    ]);
    const firebaseApp = appSdk.initializeApp(config);
    auth = authSdk.getAuth(firebaseApp);
    authMethods = authSdk;
    authSdk.onAuthStateChanged(auth, (user) => {
      currentUser = user;
      updateAuthButton();
      authReadyResolver(true);
    });
  } catch (error) {
    console.error('Firebase sign-in could not be initialized.', error);
    authReadyResolver(false);
  }
}

function setupAuthUi() {
  const nav = document.querySelector('.topbar .nav');
  if (!nav) return;

  const account = document.createElement('span');
  account.className = 'auth-user';
  account.id = 'auth-user';
  const accountButton = document.createElement('button');
  accountButton.className = 'secondary auth-button';
  accountButton.id = 'auth-button';
  accountButton.type = 'button';
  accountButton.textContent = 'Sign in';
  nav.append(account, accountButton);
  accountButton.addEventListener('click', async () => {
    await authReady;
    if (currentUser && auth) {
      await authMethods.signOut(auth);
      return;
    }
    openAuthDialog();
  });

  authDialog = document.createElement('div');
  authDialog.className = 'auth-backdrop';
  authDialog.hidden = true;
  authDialog.innerHTML = `
    <section class="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
      <button class="auth-close" type="button" aria-label="Close sign-in">&times;</button>
      <p class="eyebrow">Student account</p>
      <h2 id="auth-title">Sign in to EduGenie</h2>
      <button class="secondary google-auth-button" id="google-sign-in" type="button">Continue with Google</button>
      <form id="auth-form">
        <label for="auth-email">Email address</label>
        <input id="auth-email" type="email" autocomplete="email" required />
        <label for="auth-password">Password</label>
        <input id="auth-password" type="password" autocomplete="current-password" minlength="6" required />
        <button class="primary auth-submit" type="submit">Sign in</button>
      </form>
      <button class="auth-mode" id="auth-mode" type="button">Create an account</button>
      <button class="auth-reset" id="auth-reset" type="button">Reset password</button>
      <p class="auth-message" id="auth-message" role="status"></p>
    </section>`;
  document.body.append(authDialog);
  let creatingAccount = false;
  const form = authDialog.querySelector('#auth-form');
  const message = authDialog.querySelector('#auth-message');
  const submit = authDialog.querySelector('.auth-submit');
  const password = authDialog.querySelector('#auth-password');
  const authTitle = authDialog.querySelector('#auth-title');
  const modeButton = authDialog.querySelector('#auth-mode');

  const setAuthMode = (isCreatingAccount) => {
    creatingAccount = isCreatingAccount;
    authTitle.textContent = creatingAccount ? 'Create your account' : 'Sign in to EduGenie';
    submit.textContent = creatingAccount ? 'Create account' : 'Sign in';
    modeButton.textContent = creatingAccount ? 'Already have an account? Sign in' : 'Create an account';
    password.autocomplete = creatingAccount ? 'new-password' : 'current-password';
  };

  authDialog.querySelector('.auth-close').addEventListener('click', closeAuthDialog);
  authDialog.addEventListener('click', (event) => {
    if (event.target === authDialog) closeAuthDialog();
  });
  modeButton.addEventListener('click', () => {
    setAuthMode(!creatingAccount);
    message.textContent = '';
  });
  authDialog.querySelector('#google-sign-in').addEventListener('click', async (event) => {
    const googleButton = event.currentTarget;
    await authReady;
    if (!auth || !authMethods) {
      message.textContent = 'Google sign-in is not configured. Check the Firebase web app settings.';
      return;
    }
    googleButton.disabled = true;
    message.textContent = 'Opening Google sign-in...';
    try {
      const provider = new authMethods.GoogleAuthProvider();
      const credential = await authMethods.signInWithPopup(auth, provider);
      if (!credential.user.emailVerified) {
        await authMethods.signOut(auth);
        message.textContent = 'This Google account email is not verified. Verify it with Google, then try again.';
        return;
      }
      closeAuthDialog();
    } catch (error) {
      const messages = {
        'auth/popup-closed-by-user': 'Google sign-in was cancelled.',
        'auth/popup-blocked': 'Allow pop-ups for this site, then try Google sign-in again.',
        'auth/unauthorized-domain': 'This website domain is not authorized in Firebase Authentication.',
        'auth/operation-not-allowed': 'Google sign-in is disabled in Firebase Authentication.',
        'auth/account-exists-with-different-credential': 'This email already has an account using email and password. Sign in with that password, or reset it below.',
      };
      message.textContent = messages[error.code] || 'Google sign-in failed. Please try again.';
    } finally {
      googleButton.disabled = false;
    }
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    await authReady;
    if (!auth || !authMethods) {
      message.textContent = 'Email sign-in is not configured yet. Add your Firebase web app values to .env and restart EduGenie.';
      return;
    }
    submit.disabled = true;
    message.textContent = creatingAccount ? 'Creating your account...' : 'Signing in...';
    try {
      const email = authDialog.querySelector('#auth-email').value.trim();
      const secret = password.value;
      if (creatingAccount) {
        const credential = await authMethods.createUserWithEmailAndPassword(auth, email, secret);
        await authMethods.sendEmailVerification(credential.user);
        await authMethods.signOut(auth);
        message.textContent = 'Account created. Verify the link sent to your email, then sign in.';
      } else {
        const credential = await authMethods.signInWithEmailAndPassword(auth, email, secret);
        if (!credential.user.emailVerified) {
          try {
            await authMethods.sendEmailVerification(credential.user);
            message.textContent = 'Your email is not verified yet. We sent a new verification link. Check your inbox and spam folder, verify it, then sign in again.';
          } catch (verificationError) {
            const verificationMessages = {
              'auth/too-many-requests': 'Your email is not verified yet, and Firebase is limiting verification emails. Wait a few minutes, then try signing in again.',
              'auth/network-request-failed': 'Your email is not verified yet. Check your internet connection, then try signing in again to resend the verification link.',
            };
            message.textContent = verificationMessages[verificationError.code] || 'Your email is not verified yet. Check your inbox and spam folder for the verification link, then sign in again.';
          } finally {
            await authMethods.signOut(auth);
          }
        } else {
          closeAuthDialog();
        }
      }
    } catch (error) {
      const messages = {
        'auth/invalid-credential': 'We could not sign you in with that email and password. Check the password or use Reset password. If you created this account with Google, choose Continue with Google.',
        'auth/weak-password': 'Choose a password with at least 6 characters.',
        'auth/invalid-email': 'Enter a valid email address.',
        'auth/too-many-requests': 'Too many attempts. Wait a little and try again.',
        'auth/unauthorized-domain': 'This website address is not authorized in Firebase. Add 127.0.0.1 under Authentication > Settings > Authorized domains.',
        'auth/operation-not-allowed': 'Email/password sign-in is disabled in Firebase. Use Continue with Google, or ask the Firebase project owner to enable Email/Password.',
        'auth/network-request-failed': 'Could not reach Firebase Authentication. Check your internet connection and try again.',
      };
      if (error.code === 'auth/email-already-in-use' && creatingAccount) {
        setAuthMode(false);
        password.value = '';
        password.focus();
        message.textContent = 'This email already has an account, so I switched to sign-in. Enter your password, choose Continue with Google if you originally used Google, or use Reset password if needed.';
      } else {
        message.textContent = messages[error.code] || 'Sign-in failed. Check your details and try again.';
      }
    } finally {
      submit.disabled = false;
    }
  });
  authDialog.querySelector('#auth-reset').addEventListener('click', async () => {
    await authReady;
    const email = authDialog.querySelector('#auth-email').value.trim();
    if (!auth || !email) {
      message.textContent = 'Enter your email address first.';
      return;
    }
    try {
      await authMethods.sendPasswordResetEmail(auth, email);
      message.textContent = 'If an account exists for that address, a reset link has been sent.';
    } catch (error) {
      const resetMessages = {
        'auth/invalid-email': 'Enter a valid email address, then request a reset link.',
        'auth/too-many-requests': 'Too many reset attempts. Wait a few minutes and try again.',
        'auth/unauthorized-domain': 'This website address is not authorized in Firebase Authentication.',
        'auth/network-request-failed': 'Could not reach Firebase. Check your internet connection and try again.',
      };
      message.textContent = resetMessages[error.code] || 'Could not send a reset link. Check the email address and Firebase Authentication settings, then try again.';
    }
  });
}

function updateAuthButton() {
  const button = document.getElementById('auth-button');
  const email = document.getElementById('auth-user');
  if (!button || !email) return;
  button.textContent = currentUser ? 'Sign out' : 'Sign in';
  button.title = currentUser?.email || 'Sign in with Google or email';
  email.textContent = currentUser?.email || '';
}

function openAuthDialog() {
  if (authDialog) {
    authDialog.hidden = false;
    authDialog.querySelector('#auth-email').focus();
  }
}

function closeAuthDialog() {
  if (authDialog) authDialog.hidden = true;
}

async function requestApi(url, options = {}) {
  await authReady;
  if (!auth || !currentUser) {
    openAuthDialog();
    throw new Error('Sign in with your verified email to use this feature.');
  }
  const token = await currentUser.getIdToken();
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
      Authorization: `Bearer ${token}`,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'The request could not be completed. Please try again.');
  return data;
}

setupAuthUi();
initializeFirebaseAuth();

const chatBox = document.getElementById('chat-box');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const voiceBtn = document.getElementById('voice-btn');
const subjectSelect = document.getElementById('subject-select');
const levelSelect = document.getElementById('level-select');
const ageSelect = document.getElementById('age-select');
const quizBox = document.getElementById('quiz-box');
const generateQuizBtn = document.getElementById('generate-quiz');

function appendInlineMarkdown(parent, text) {
  const pattern = /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|`([^`\n]+)`|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*\n]+)\*|_([^_\n]+)_)/g;
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    const [token, , linkText, linkUrl, codeText, boldAsterisk, boldUnderscore, italicAsterisk, italicUnderscore] = match;
    parent.append(document.createTextNode(text.slice(lastIndex, match.index)));
    if (linkText && linkUrl) {
      const link = document.createElement('a');
      link.href = linkUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = linkText;
      parent.append(link);
    } else if (codeText) {
      const code = document.createElement('code');
      code.textContent = codeText;
      parent.append(code);
    } else if (boldAsterisk || boldUnderscore) {
      const strong = document.createElement('strong');
      strong.textContent = boldAsterisk || boldUnderscore;
      parent.append(strong);
    } else {
      const emphasis = document.createElement('em');
      emphasis.textContent = italicAsterisk || italicUnderscore;
      parent.append(emphasis);
    }
    lastIndex = match.index + token.length;
  }
  parent.append(document.createTextNode(text.slice(lastIndex)));
}

function renderMarkdown(parent, content) {
  parent.classList.add('markdown-content');
  parent.replaceChildren();
  const lines = String(content).replace(/\r\n?/g, '\n').split('\n');
  let paragraph = [];
  let list = null;
  let codeLines = null;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    const element = document.createElement('p');
    appendInlineMarkdown(element, paragraph.join(' '));
    parent.append(element);
    paragraph = [];
  };
  const flushList = () => {
    if (list) parent.append(list);
    list = null;
  };

  for (const line of lines) {
    if (/^\s*```/.test(line)) {
      flushParagraph();
      flushList();
      if (codeLines) {
        const pre = document.createElement('pre');
        const code = document.createElement('code');
        code.textContent = codeLines.join('\n');
        pre.append(code);
        parent.append(pre);
        codeLines = null;
      } else {
        codeLines = [];
      }
      continue;
    }
    if (codeLines) {
      codeLines.push(line);
      continue;
    }

    const headingMatch = line.match(/^\s{0,3}(#{1,6})\s+(.+)$/);
    const listMatch = line.match(/^\s*(?:([-*+])|(\d+)[.)])\s+(.+)$/);
    if (!line.trim()) {
      flushParagraph();
      flushList();
    } else if (headingMatch) {
      flushParagraph();
      flushList();
      const heading = document.createElement(`h${Math.min(headingMatch[1].length + 1, 6)}`);
      appendInlineMarkdown(heading, headingMatch[2]);
      parent.append(heading);
    } else if (listMatch) {
      flushParagraph();
      const isOrdered = Boolean(listMatch[2]);
      if (!list || (list.tagName === 'OL') !== isOrdered) {
        flushList();
        list = document.createElement(isOrdered ? 'ol' : 'ul');
      }
      const item = document.createElement('li');
      appendInlineMarkdown(item, listMatch[3]);
      list.append(item);
    } else if (/^\s*>\s?/.test(line)) {
      flushParagraph();
      flushList();
      const quote = document.createElement('blockquote');
      appendInlineMarkdown(quote, line.replace(/^\s*>\s?/, ''));
      parent.append(quote);
    } else if (/^\s*(?:[-*_]\s*){3,}$/.test(line)) {
      flushParagraph();
      flushList();
      parent.append(document.createElement('hr'));
    } else {
      flushList();
      paragraph.push(line.trim());
    }
  }
  if (codeLines) {
    const pre = document.createElement('pre');
    const code = document.createElement('code');
    code.textContent = codeLines.join('\n');
    pre.append(code);
    parent.append(pre);
  }
  flushParagraph();
  flushList();
}

function addMessage(role, content) {
  if (!chatBox) return;
  const el = document.createElement('div');
  el.className = `message ${role}`;
  if (role === 'assistant') renderMarkdown(el, content);
  else el.textContent = content;
  chatBox.appendChild(el);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function setLoading(isLoading) {
  if (!chatBox) return;
  if (isLoading) {
    const loader = document.createElement('div');
    loader.className = 'message assistant';
    loader.textContent = 'EduGenie is thinking...';
    loader.id = 'loader-message';
    chatBox.appendChild(loader);
  } else {
    const loader = document.getElementById('loader-message');
    if (loader) loader.remove();
  }
}

async function sendChat() {
  if (!chatInput || !subjectSelect || !levelSelect || !ageSelect) return;
  const text = chatInput.value.trim();
  if (!text) {
    addMessage('assistant', 'Type a question first, then send it to EduGenie.');
    return;
  }

  addMessage('user', text);
  chatInput.value = '';
  setLoading(true);

  try {
    const data = await requestApi('/qa', {
      method: 'POST',
      body: JSON.stringify({ question: text, subject: subjectSelect.value, level: levelSelect.value, age_group: ageSelect.value }),
    });
    addMessage('assistant', data.answer || 'No response received.');
    if (data.history_warning) addMessage('assistant', data.history_warning);
  } catch (error) {
    addMessage('assistant', error.message);
  } finally {
    setLoading(false);
  }
}

if (sendBtn) sendBtn.addEventListener('click', sendChat);
if (chatInput) {
  chatInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendChat();
    }
  });
}

if (voiceBtn) {
  voiceBtn.addEventListener('click', () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      addMessage('assistant', 'Microphone input is not supported in this browser. Please use Chrome or Edge, or type your question manually.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      voiceBtn.textContent = 'Listening...';
      voiceBtn.disabled = true;
      addMessage('assistant', 'Listening... speak now.');
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (chatInput) {
        chatInput.value = transcript;
      }
      addMessage('user', transcript);
    };

    recognition.onerror = (event) => {
      const message = event.error === 'not-allowed'
        ? 'Microphone permission was denied. Please allow mic access and try again.'
        : 'Microphone input failed. Please type your question instead.';
      addMessage('assistant', message);
    };

    recognition.onend = () => {
      voiceBtn.textContent = '🎙️ Speak';
      voiceBtn.disabled = false;
    };

    try {
      recognition.start();
    } catch (error) {
      addMessage('assistant', 'The microphone is already active. Please wait a moment and try again.');
      voiceBtn.textContent = '🎙️ Speak';
      voiceBtn.disabled = false;
    }
  });
}

async function loadCourses() {
  const container = document.getElementById('courses-container');
  if (!container) return;

  const response = await fetch('/api/courses');
  const data = await response.json();
  container.innerHTML = data.courses.map(course => `
    <div class="course-card">
      <div class="meta">${course.level} · ${course.duration}</div>
      <h3>${course.title}</h3>
      <p>${course.description}</p>
      <div class="tags">
        ${course.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

async function loadRoadmaps() {
  const container = document.getElementById('roadmap-container');
  if (!container) return;

  const response = await fetch('/api/roadmaps');
  const data = await response.json();
  container.innerHTML = data.roadmaps.map(roadmap => `
    <div class="roadmap-card">
      <div class="meta">${roadmap.timeline}</div>
      <h3>${roadmap.title}</h3>
      <ul>
        ${roadmap.outcomes.map(item => `<li>${item}</li>`).join('')}
      </ul>
    </div>
  `).join('');
}

async function generateQuiz() {
  if (!quizBox) return;
  const text = document.getElementById('quiz-topic').value.trim();
  if (!text) {
    quizBox.textContent = 'Enter a topic or paste a passage first.';
    return;
  }
  quizBox.textContent = 'Generating three questions...';
  try {
    const data = await requestApi('/quiz', {
      method: 'POST',
      body: JSON.stringify({ text, subject: document.getElementById('quiz-subject').value, level: document.getElementById('quiz-level').value }),
    });
    quizBox.replaceChildren();
    data.questions.forEach((question, index) => {
      const item = document.createElement('article');
      item.className = 'quiz-item';
      const title = document.createElement('h4');
      title.append(document.createTextNode(`${index + 1}. `));
      appendInlineMarkdown(title, question.question);
      const options = document.createElement('div');
      options.className = 'quiz-options';
      const feedback = document.createElement('div');
      feedback.className = 'quiz-feedback';
      Object.entries(question.options).forEach(([letter, label]) => {
        const option = document.createElement('button');
        option.className = 'quiz-option';
        option.type = 'button';
        option.append(document.createTextNode(`${letter}. `));
        appendInlineMarkdown(option, label);
        option.addEventListener('click', () => {
          options.querySelectorAll('button').forEach((button) => { button.disabled = true; });
          const correct = letter === question.correct_answer;
          option.classList.add(correct ? 'correct' : 'incorrect');
          if (!correct) options.querySelectorAll('button').forEach((button) => {
            if (button.textContent.startsWith(`${question.correct_answer}.`)) button.classList.add('correct');
          });
          const result = document.createElement('p');
          result.textContent = `${correct ? 'Correct.' : `Not quite. The correct answer is ${question.correct_answer}.`}`;
          const explanation = document.createElement('div');
          renderMarkdown(explanation, question.explanation);
          feedback.replaceChildren(result, explanation);
        });
        options.append(option);
      });
      item.append(title, options, feedback);
      quizBox.append(item);
    });
  } catch (error) {
    quizBox.textContent = error.message;
  }
}

async function generateSummary() {
  const textArea = document.getElementById('summary-input');
  const summaryBox = document.getElementById('summary-output');
  if (!textArea || !summaryBox) return;

  const text = textArea.value.trim();
  if (!text) {
    summaryBox.textContent = 'Please paste some study material to summarize.';
    return;
  }

  summaryBox.textContent = 'Summarizing...';
  try {
    const data = await requestApi('/summarize', { method: 'POST', body: JSON.stringify({ text }) });
    renderMarkdown(summaryBox, data.summary || 'Unable to generate summary right now.');
  } catch (error) {
    summaryBox.textContent = error.message;
  }
}

async function generateExplanation() {
  const topicInput = document.getElementById('explain-topic-input');
  const output = document.getElementById('explain-topic-output');
  if (!topicInput || !output) return;
  const topic = topicInput.value.trim();
  if (!topic) {
    output.textContent = 'Enter a topic to explain.';
    return;
  }
  output.textContent = 'Preparing a beginner-friendly explanation...';
  try {
    const data = await requestApi('/explain', { method: 'POST', body: JSON.stringify({ topic }) });
    renderMarkdown(output, data.explanation || 'Unable to explain this topic right now.');
  } catch (error) {
    output.textContent = error.message;
  }
}

async function generateLearningPlan() {
  const subject = document.getElementById('plan-subject');
  const goal = document.getElementById('plan-goal');
  const level = document.getElementById('plan-level');
  const output = document.getElementById('path-output');
  if (!subject || !goal || !level || !output) return;
  const topic = subject.value.trim();
  if (!topic) {
    output.textContent = 'Type a topic you want to learn first.';
    subject.focus();
    return;
  }

  const button = document.getElementById('generate-path');
  if (button) button.disabled = true;
  output.textContent = 'EduGenie is building your personalized roadmap...';
  try {
    const data = await requestApi('/learn/recommendations', {
      method: 'POST',
      body: JSON.stringify({ topic, goal: goal.value.trim(), level: level.value }),
    });
    const stages = data.learning_path;
    if (!stages || typeof stages !== 'object') {
      throw new Error('EduGenie returned an incomplete roadmap. Please try again.');
    }

    const title = document.createElement('h3');
    title.textContent = `Your ${topic} roadmap`;
    const goalDescription = document.createElement('p');
    goalDescription.textContent = `Goal: ${goal.value.trim() || 'General learning'} · Starting level: ${level.value}`;
    const grid = document.createElement('div');
    grid.className = 'path-grid';

    const appendList = (card, label, items) => {
      if (!Array.isArray(items) || !items.length) return;
      const heading = document.createElement('h4');
      heading.textContent = label;
      const list = document.createElement('ul');
      items.forEach((item) => {
        const entry = document.createElement('li');
        appendInlineMarkdown(entry, String(item));
        list.append(entry);
      });
      card.append(heading, list);
    };

    [
      ['beginner', 'Beginner'],
      ['intermediate', 'Intermediate'],
      ['advanced', 'Advanced'],
    ].forEach(([key, label]) => {
      const stage = stages[key];
      if (!stage || typeof stage !== 'object') return;
      const card = document.createElement('article');
      card.className = 'path-card';
      const stageTitle = document.createElement('h3');
      stageTitle.textContent = label;
      card.append(stageTitle);
      if (typeof stage.explanation === 'string') {
        const explanation = document.createElement('div');
        renderMarkdown(explanation, stage.explanation);
        card.append(explanation);
      }
      appendList(card, 'Topics', stage.topics);
      appendList(card, 'Study order', stage.learning_order);
      appendList(card, 'Practice', stage.practice);
      appendList(card, 'Resources', stage.resources);
      grid.append(card);
    });

    if (!grid.childElementCount) {
      throw new Error('EduGenie returned an incomplete roadmap. Please try again.');
    }
    output.replaceChildren(title, goalDescription, grid);
  } catch (error) {
    output.textContent = error.message;
  } finally {
    if (button) button.disabled = false;
  }
}

const scrollToChatBtn = document.getElementById('scroll-to-chat');
if (scrollToChatBtn) {
  scrollToChatBtn.addEventListener('click', () => {
    document.getElementById('ai-tutor').scrollIntoView({ behavior: 'smooth' });
  });
}

const scrollToCoursesBtn = document.getElementById('scroll-to-courses');
if (scrollToCoursesBtn) {
  scrollToCoursesBtn.addEventListener('click', () => {
    document.getElementById('courses').scrollIntoView({ behavior: 'smooth' });
  });
}

if (generateQuizBtn) generateQuizBtn.addEventListener('click', generateQuiz);

const summarizeBtn = document.getElementById('summarize-btn');
if (summarizeBtn) summarizeBtn.addEventListener('click', generateSummary);

const explainTopicBtn = document.getElementById('explain-topic-btn');
if (explainTopicBtn) explainTopicBtn.addEventListener('click', generateExplanation);

const learningPlanBtn = document.getElementById('generate-path');
if (learningPlanBtn) learningPlanBtn.addEventListener('click', generateLearningPlan);

if (document.body.dataset.page === 'ai-tutor' && chatBox) {
  addMessage('assistant', 'Welcome to EduGenie. Ask me about Python, Java, DSA, DBMS, OS, or study strategy and I will guide you.');
}

if (document.getElementById('courses-container')) loadCourses();
if (document.getElementById('roadmap-container')) loadRoadmaps();
