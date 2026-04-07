/**
 * @name ArduinoMute
 * @author Francesco
 * @version 1.0.0
 * @description Controls Discord microphone and audio mute via external Arduino controller
 */

module.exports = class ArduinoMute {

  constructor() {
    // Discord modules
    this.VoiceActions = null;
    this.VoiceStateStore = null;
    
    // WebSocket connection
    this.ws = null;
    this.reconnectAttempts = 0;
    
    // State tracking
    this.micMuted = false;
    this.audioDeafened = false;
    this.stateMonitorId = null;
    this.lastSyncTime = 0;
    
    // Configuration constants
    this.SERVER_URL = "ws://localhost:8765";
    this.STATE_UPDATE_DELAY = 100;
    this.RECONNECT_DELAY = 2000;
    this.MAX_RECONNECT_ATTEMPTS = 10;
    this.STATE_MONITOR_INTERVAL = 500;
    this.MIN_SYNC_INTERVAL = 300; // Evita sincronizzazioni troppo frequenti
  }

  start() {
    console.log("[ArduinoMute] Plugin started v1.0.0");

    // Load Discord VoiceActions module
    this.VoiceActions = this.findVoiceActions();
    if (!this.VoiceActions) {
      console.error("[ArduinoMute] VoiceActions not found!");
      return;
    }

    // Load VoiceStateStore for state querying
    this.VoiceStateStore = this.findVoiceStateStore();
    
    // Get initial state
    this.updateCurrentState();
    console.log("[ArduinoMute] Initial state - Mic:", this.micMuted, "Audio:", this.audioDeafened);

    // Start monitoring Discord state for changes
    this.startStateMonitoring();

    // Connect to Python server
    this.connectToServer();
  }

  updateCurrentState() {
    const modules = [this.VoiceStateStore, this.VoiceActions];
    
    for (const module of modules) {
      if (!module) continue;
      
      try {
        const hasMute = typeof module.isSelfMute === "function";
        const hasDeaf = typeof module.isSelfDeaf === "function";
        
        if (hasMute) this.micMuted = module.isSelfMute();
        if (hasDeaf) this.audioDeafened = module.isSelfDeaf();
        
        if (hasMute || hasDeaf) return; // Esci una volta trovati i dati
      } catch (e) {
        console.warn("[ArduinoMute] Error reading state:", e.message);
      }
    }
  }

  findVoiceActions() {
    const predicates = [
      m => m.toggleSelfMute && m.toggleSelfDeaf && m.isSelfMute,
      m => m.toggleSelfDeaf,
      m => m.toggleSelfMute
    ];
    
    for (const predicate of predicates) {
      try {
        const module = BdApi.Webpack.getModule(predicate);
        if (module) {
          console.log("[ArduinoMute] VoiceActions found");
          return module;
        }
      } catch (e) {
        console.warn("[ArduinoMute] VoiceActions search error:", e.message);
      }
    }

    console.error("[ArduinoMute] VoiceActions not found!");
    return null;
  }

  findVoiceStateStore() {
    const predicates = [
      m => m.isSelfMute && m.isSelfDeaf,
      m => m.isSelfMute
    ];
    
    for (const predicate of predicates) {
      try {
        const module = BdApi.Webpack.getModule(predicate);
        if (module) {
          console.log("[ArduinoMute] VoiceStateStore found");
          return module;
        }
      } catch (e) {
        console.warn("[ArduinoMute] VoiceStateStore search error:", e.message);
      }
    }

    try {
      const module = BdApi.findModuleByProps?.("isSelfMute", "isSelfDeaf");
      if (module) {
        console.log("[ArduinoMute] VoiceStateStore found (via props)");
        return module;
      }
    } catch (e) {
      // Expected if method not available
    }

    console.warn("[ArduinoMute] VoiceStateStore not found");
    return null;
  }

  connectToServer() {
    try {
      this.ws = new WebSocket(this.SERVER_URL);
      this.ws.onopen = this.onWebSocketOpen.bind(this);
      this.ws.onmessage = this.onWebSocketMessage.bind(this);
      this.ws.onerror = this.onWebSocketError.bind(this);
      this.ws.onclose = this.onWebSocketClose.bind(this);
    } catch (e) {
      console.error("[ArduinoMute] Connection error:", e.message);
      this.attemptReconnect();
    }
  }

  onWebSocketOpen() {
    console.log("[ArduinoMute] Connected to server");
    this.reconnectAttempts = 0;
    this.ws.send(JSON.stringify({ type: 'query_state' }));
    this.syncLEDs();
  }

  onWebSocketMessage(event) {
    try {
      const data = JSON.parse(event.data);
      this.handleServerMessage(data);
    } catch (e) {
      console.error("[ArduinoMute] Parse error:", e.message);
    }
  }

  onWebSocketError(error) {
    console.error("[ArduinoMute] WebSocket error:", error.message || error);
  }

  onWebSocketClose() {
    console.warn("[ArduinoMute] Disconnected from server");
    this.attemptReconnect();
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.MAX_RECONNECT_ATTEMPTS) {
      this.reconnectAttempts++;
      // Exponential backoff: 2s, 4s, 8s, ...
      const delay = this.RECONNECT_DELAY * Math.min(Math.pow(2, this.reconnectAttempts - 1), 16);
      console.log(`[ArduinoMute] Reconnecting ${this.reconnectAttempts}/${this.MAX_RECONNECT_ATTEMPTS} in ${delay}ms...`);
      setTimeout(() => this.connectToServer(), delay);
    } else {
      console.error("[ArduinoMute] Max reconnection attempts reached");
    }
  }

  handleServerMessage(data) {
    const { type, action, muted, deafened } = data;

    if (type === 'button_pressed') {
      const buttonAction = action || 'mic';
      console.log(`[ArduinoMute] Button pressed: ${buttonAction}`);
      this.performAction(buttonAction);
    } else if (type === 'state') {
      this.updateCurrentState();
      // Sincronizza solo se lo stato è diverso
      if (this.micMuted !== muted || this.audioDeafened !== deafened) {
        if (this.micMuted !== muted) this.toggleMic();
        if (this.audioDeafened !== deafened) this.toggleAudio();
      }
    }
  }

  performAction(action) {
    switch (action) {
      case 'mic':
        this.toggleMic();
        break;
      case 'audio':
        this.toggleAudio();
        break;
      case 'toggle_both':
        this.toggleBoth();
        break;
      default:
        console.warn(`[ArduinoMute] Unknown action: ${action}`);
    }
  }

  performToggle(action, label) {
    if (!this.VoiceActions?.[action]) {
      console.error(`[ArduinoMute] ${action} not available`);
      return;
    }

    try {
      this.VoiceActions[action]();
      
      setTimeout(() => {
        try {
          this.updateCurrentState();
          console.log(`[ArduinoMute] ${label} toggled`);
          this.sendStateToServer();
          this.syncLEDs();
        } catch (e) {
          console.error(`[ArduinoMute] Error after toggle:`, e.message);
        }
      }, this.STATE_UPDATE_DELAY);
    } catch (e) {
      console.error(`[ArduinoMute] Error toggling ${label}:`, e.message);
    }
  }

  toggleMic() {
    this.performToggle("toggleSelfMute", "Mic");
  }

  toggleAudio() {
    this.performToggle("toggleSelfDeaf", "Audio");
  }

  toggleBoth() {
    if (!this.VoiceActions?.toggleSelfMute) {
      console.error("[ArduinoMute] VoiceActions not available");
      return;
    }
    console.log("[ArduinoMute] Toggling both mic and audio");
    this.toggleMic();
    this.toggleAudio();
  }

  sendStateToServer() {
    if (!this.isWebSocketReady()) return;
    
    try {
      this.ws.send(JSON.stringify({
        type: 'state_update',
        muted: this.micMuted,
        deafened: this.audioDeafened
      }));
    } catch (e) {
      console.error("[ArduinoMute] Error sending state:", e.message);
    }
  }

  syncLEDs() {
    // Debouncing: evita sincronizzazioni troppo frequenti
    const now = Date.now();
    if (now - this.lastSyncTime < this.MIN_SYNC_INTERVAL) return;
    
    if (!this.isWebSocketReady()) return;
    
    try {
      this.lastSyncTime = now;
      this.ws.send(JSON.stringify({
        type: 'sync_leds',
        mic_led: this.micMuted,
        audio_led: this.audioDeafened
      }));
      console.log("[ArduinoMute] LEDs synced - Mic:", this.micMuted, "Audio:", this.audioDeafened);
    } catch (e) {
      console.error("[ArduinoMute] Error syncing LEDs:", e.message);
    }
  }

  isWebSocketReady() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  startStateMonitoring() {
    this.stateMonitorId = setInterval(() => {
      const prevMic = this.micMuted;
      const prevAudio = this.audioDeafened;
      
      this.updateCurrentState();
      
      // Sincronizza solo se lo stato è effettivamente cambiato
      if (prevMic !== this.micMuted || prevAudio !== this.audioDeafened) {
        console.log("[ArduinoMute] State changed - Mic:", this.micMuted, "Audio:", this.audioDeafened);
        this.syncLEDs();
      }
    }, this.STATE_MONITOR_INTERVAL);
  }

  stopStateMonitoring() {
    if (this.stateMonitorId !== null) {
      clearInterval(this.stateMonitorId);
      this.stateMonitorId = null;
      console.log("[ArduinoMute] State monitoring stopped");
    }
  }

  stop() {
    console.log("[ArduinoMute] Plugin stopped");
    this.stopStateMonitoring();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
};