/* Kameen voice calls. ES module; shared helpers such as api() live on window (app.js).
   No key or agent ID is kept here: the server hands back a signed link or an agent ID for each call. */
import { Conversation } from 'https://cdn.jsdelivr.net/npm/@elevenlabs/client/+esm';

let call = null;       // the live ElevenLabs conversation, if any
let timer = null;      // hard stop after maxSeconds
let micStream = null;  // the stream opened to ask for microphone permission
let announced = true;  // whether "call ended" was already announced for the current call

function emit(name, detail) {
  window.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
}

function releaseMic() {
  if (micStream) {
    micStream.getTracks().forEach(function (track) { track.stop(); });
    micStream = null;
  }
}

function announceEnd() {
  if (announced) return;
  announced = true;
  emit('kameen:call-ended');
}

export async function startCall(conversationId, maxSeconds) {
  if (call) await endCall();
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error('This browser cannot use the microphone on this page.');
  }
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const session = await window.api('/voice/session', { conversation_id: conversationId });
    // A private agent comes with a signed link; a public agent comes with its ID.
    const target = session.signed_url ? { signedUrl: session.signed_url }
      : (session.agent_id ? { agentId: session.agent_id } : null);
    if (!target) throw new Error('The server did not return a voice session.');
    announced = false;
    call = await Conversation.startSession({
      ...target,
      connectionType: 'websocket',
      dynamicVariables: session.dynamic_variables || {},
      onDisconnect: function () {
        clearTimeout(timer);
        timer = null;
        call = null;
        releaseMic();
        announceEnd();
      },
      onError: function (message) {
        emit('kameen:call-error', { message: String(message || 'Voice error') });
      },
      onModeChange: function (info) {
        emit('kameen:call-mode', { mode: info && info.mode });
      }
    });
    timer = setTimeout(endCall, maxSeconds * 1000);
  } catch (err) {
    clearTimeout(timer);
    timer = null;
    call = null;
    announced = true;
    releaseMic();
    throw err;
  }
}

export async function endCall() {
  clearTimeout(timer);
  timer = null;
  const current = call;
  call = null;
  if (current) {
    try { await current.endSession(); } catch (err) { /* already closed */ }
  }
  releaseMic();
  announceEnd();
}

window.kameenVoice = { startCall, endCall };
