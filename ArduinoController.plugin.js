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
    this.SERVER_URL = "ws://localhost:8765";
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 2000;
    
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
    // Try to read state from VoiceStateStore
    if (this.VoiceStateStore) {
      try {
        if (typeof this.VoiceStateStore.isSelfMute === "function") {
          this.micMuted = this.VoiceStateStore.isSelfMute();
        }
        if (typeof this.VoiceStateStore.isSelfDeaf === "function") {
          this.audioDeafened = this.VoiceStateStore.isSelfDeaf();
        }
      } catch (e) {
        console.warn("[ArduinoMute] Error reading state from VoiceStateStore:", e);
      }
    }
    
    // Fallback: read state from VoiceActions
    if (this.VoiceActions) {
      try {
        if (typeof this.VoiceActions.isSelfMute === "function") {
          this.micMuted = this.VoiceActions.isSelfMute();
        }
        if (typeof this.VoiceActions.isSelfDeaf === "function") {
          this.audioDeafened = this.VoiceActions.isSelfDeaf();
        }
      } catch (e) {
        console.warn("[ArduinoMute] Error reading state from VoiceActions:", e);
      }
    }
  }

  findVoiceActions() {
    // Try to find complete module with all functions
    let module = BdApi.Webpack.getModule(
      m => typeof m.toggleSelfMute === "function" && typeof m.toggleSelfDeaf === "function" && typeof m.isSelfMute === "function"
    );
    if (module) {
      console.log("[ArduinoMute] VoiceActions found (complete module)");
      return module;
    }

    // Fallback: search for toggleSelfDeaf only
    module = BdApi.Webpack.getModule(
      m => typeof m.toggleSelfDeaf === "function"
    );
    if (module) {
      console.log("[ArduinoMute] VoiceActions found (deafen only)");
      return module;
    }

    // Fallback: search for toggleSelfMute (minimum)
    module = BdApi.Webpack.getModule(
      m => typeof m.toggleSelfMute === "function"
    );
    if (module) {
      console.log("[ArduinoMute] VoiceActions found (mute only)");
      return module;
    }

    console.error("[ArduinoMute] No VoiceActions module found!");
    return null;
  }

  findVoiceStateStore() {
    // Search for module with both isSelfMute and isSelfDeaf functions
    let module = BdApi.Webpack.getModule(
      m => typeof m.isSelfMute === "function" && typeof m.isSelfDeaf === "function"
    );
    if (module) {
      console.log("[ArduinoMute] VoiceStateStore found");
      return module;
    }

    // Fallback: search for isSelfMute only
    module = BdApi.Webpack.getModule(
      m => typeof m.isSelfMute === "function"
    );
    if (module) {
      console.log("[ArduinoMute] VoiceStateStore found (mute only)");
      return module;
    }

    // Alternative: use findModuleByProps
    try {
      module = BdApi.findModuleByProps("isSelfMute", "isSelfDeaf");
      if (module) {
        console.log("[ArduinoMute] VoiceStateStore found (via props)");
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
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`[ArduinoMute] Reconnecting ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);
      setTimeout(() => this.connectToServer(), this.reconnectDelay);
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

  toggleMic() {
    if (!this.VoiceActions) {
      console.error("[ArduinoMute] VoiceActions not available");
      return;
    }

    try {
      this.VoiceActions.toggleSelfMute();

      setTimeout(() => {
        try {
          this.updateCurrentState();
          console.log("[ArduinoMute] Mic toggled:", this.micMuted ? "MUTED" : "UNMUTED");
          this.sendStateToServer();
        } catch (e) {
          console.error("[ArduinoMute] Error reading mute state:", e);
        }
      }, 100);
    } catch (e) {
      console.error("[ArduinoMute] Error toggling mute:", e);
    }
  }

  toggleAudio() {
    if (!this.VoiceActions) {
      console.error("[ArduinoMute] VoiceActions not available");
      return;
    }

    try {
      if (typeof this.VoiceActions.toggleSelfDeaf === "function") {
        this.VoiceActions.toggleSelfDeaf();
        
        setTimeout(() => {
          try {
            this.updateCurrentState();
            console.log("[ArduinoMute] Audio toggled:", this.audioDeafened ? "DEAFENED" : "UNDEAFENED");
            this.sendStateToServer();
          } catch (e) {
            console.error("[ArduinoMute] Error reading deaf state:", e);
          }
        }, 100);
      } else {
        console.warn("[ArduinoMute] toggleSelfDeaf not available");
        return;
      }
    } catch (e) {
      console.error("[ArduinoMute] Error toggling deafen:", e);
    }
  }

  toggleBoth() {
    if (!this.VoiceActions) {
      console.error("[ArduinoMute] VoiceActions not available");
      return;
    }

    console.log("[ArduinoMute] Toggle both mic and audio");
    
    try {
      this.VoiceActions.toggleSelfMute();
    } catch (e) {
      console.error("[ArduinoMute] Error toggling mute:", e);
    }

    try {
      if (typeof this.VoiceActions.toggleSelfDeaf === "function") {
        this.VoiceActions.toggleSelfDeaf();
      }
    } catch (e) {
      console.error("[ArduinoMute] Error toggling deafen:", e);
    }

    setTimeout(() => {
      try {
        this.updateCurrentState();
        console.log(`[ArduinoMute] State after toggle: Mic=${this.micMuted ? "MUTED" : "UNMUTED"}, Audio=${this.audioDeafened ? "DEAFENED" : "UNDEAFENED"}`);
        this.sendStateToServer();
      } catch (e) {
        console.error("[ArduinoMute] Error reading state:", e);
      }
    }, 100);
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