/**
 * @name ArduinoMute
 * @author Francesco
 * @version 1.0.0
 * @description Controls Discord microphone and audio mute via external Arduino controller
 */

module.exports = class ArduinoMute {

  constructor() {
    this.VoiceActions = null;
    this.VoiceStateStore = null;
    this.ws = null;
    
    // Configuration constants
    this.SERVER_URL = "ws://localhost:8765";
    this.STATE_UPDATE_DELAY = 100;
    this.RECONNECT_DELAY = 2000;
    this.MAX_RECONNECT_ATTEMPTS = 10;
    
    this.reconnectAttempts = 0;
    this.micMuted = false;
    this.audioDeafened = false;
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

    // Connect to Python server
    this.connectToServer();
  }

  updateCurrentState() {
    const modules = [this.VoiceStateStore, this.VoiceActions];
    
    for (const module of modules) {
      if (!module) continue;
      
      try {
        if (typeof module.isSelfMute === "function") {
          this.micMuted = module.isSelfMute();
        }
        if (typeof module.isSelfDeaf === "function") {
          this.audioDeafened = module.isSelfDeaf();
        }
        if (this.micMuted !== undefined || this.audioDeafened !== undefined) {
          return;
        }
      } catch (e) {
        console.warn("[ArduinoMute] Error reading state:", e);
      }
    }
  }

  findVoiceActions() {
    const predicates = [
      m => typeof m.toggleSelfMute === "function" && typeof m.toggleSelfDeaf === "function" && typeof m.isSelfMute === "function",
      m => typeof m.toggleSelfDeaf === "function",
      m => typeof m.toggleSelfMute === "function"
    ];
    
    for (const predicate of predicates) {
      const module = BdApi.Webpack.getModule(predicate);
      if (module) {
        console.log("[ArduinoMute] VoiceActions found");
        return module;
      }
    }

    console.error("[ArduinoMute] No VoiceActions module found!");
    return null;
  }

  findVoiceStateStore() {
    const predicates = [
      m => typeof m.isSelfMute === "function" && typeof m.isSelfDeaf === "function",
      m => typeof m.isSelfMute === "function"
    ];
    
    for (const predicate of predicates) {
      const module = BdApi.Webpack.getModule(predicate);
      if (module) {
        console.log("[ArduinoMute] VoiceStateStore found");
        return module;
      }
    }

    try {
      const module = BdApi.findModuleByProps("isSelfMute", "isSelfDeaf");
      if (module) {
        console.log("[ArduinoMute] VoiceStateStore found");
        return module;
      }
    } catch (e) {
      console.log("[ArduinoMute] findModuleByProps not available");
    }

    console.warn("[ArduinoMute] VoiceStateStore not found");
    return null;
  }

  connectToServer() {
    try {
      this.ws = new WebSocket(this.SERVER_URL);

      this.ws.onopen = () => {
        console.log("[ArduinoMute] Connected to server");
        this.reconnectAttempts = 0;
        this.ws.send(JSON.stringify({ type: 'query_state' }));
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleServerMessage(data);
        } catch (e) {
          console.error("[ArduinoMute] Parse error:", e);
        }
      };

      this.ws.onerror = (error) => {
        console.error("[ArduinoMute] WebSocket error:", error);
      };

      this.ws.onclose = () => {
        console.warn("[ArduinoMute] Disconnected from server");
        this.attemptReconnect();
      };

    } catch (e) {
      console.error("[ArduinoMute] Connection error:", e);
      this.attemptReconnect();
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.MAX_RECONNECT_ATTEMPTS) {
      this.reconnectAttempts++;
      console.log(`[ArduinoMute] Reconnecting ${this.reconnectAttempts}/${this.MAX_RECONNECT_ATTEMPTS}...`);
      setTimeout(() => this.connectToServer(), this.RECONNECT_DELAY);
    } else {
      console.error("[ArduinoMute] Max reconnection attempts reached");
    }
  }

  handleServerMessage(data) {
    const msgType = data.type;

    if (msgType === 'button_pressed') {
      // Button pressed on Arduino
      const action = data.action || 'mic';
      console.log(`[ArduinoMute] Button pressed: ${action}`);
      
      if (action === 'mic') {
        this.toggleMic();
      } else if (action === 'audio') {
        this.toggleAudio();
      } else if (action === 'toggle_both') {
        this.toggleBoth();
      }

    } else if (msgType === 'state') {
      // State update from server
      this.updateCurrentState();
      const serverMuted = data.muted;
      const serverDeafened = data.deafened;
      
      // Sync if Discord state differs from server
      if (this.micMuted !== serverMuted) {
        this.toggleMic();
      }
      
      if (this.audioDeafened !== serverDeafened) {
        this.toggleAudio();
      }
    }
  }

  performToggle(action, label) {
    if (!this.VoiceActions) {
      console.error("[ArduinoMute] VoiceActions not available");
      return;
    }

    try {
      if (typeof this.VoiceActions[action] === "function") {
        this.VoiceActions[action]();
      } else {
        console.warn(`[ArduinoMute] ${action} not available`);
        return;
      }
      
      setTimeout(() => {
        try {
          this.updateCurrentState();
          console.log(`[ArduinoMute] ${label} toggled`);
          this.sendStateToServer();
        } catch (e) {
          console.error(`[ArduinoMute] Error toggling ${label.toLowerCase()}:`, e);
        }
      }, this.STATE_UPDATE_DELAY);
    } catch (e) {
      console.error(`[ArduinoMute] Error toggling ${label.toLowerCase()}:`, e);
    }
  }

  toggleMic() {
    this.performToggle("toggleSelfMute", "Mic");
  }

  toggleAudio() {
    this.performToggle("toggleSelfDeaf", "Audio");
  }

  toggleBoth() {
    if (!this.VoiceActions) {
      console.error("[ArduinoMute] VoiceActions not available");
      return;
    }

    console.log("[ArduinoMute] Toggle both mic and audio");
    this.performToggle("toggleSelfMute", "Mic");
    this.performToggle("toggleSelfDeaf", "Audio");
  }

  sendStateToServer() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'state_update',
        muted: this.micMuted,
        deafened: this.audioDeafened
      }));
    }
  }

  stop() {
    console.log("[ArduinoMute] Plugin stopped");
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
};