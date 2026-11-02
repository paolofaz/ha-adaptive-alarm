/**
 * Adaptive Alarm: standalone Lovelace status card for existing dashboards.
 * Native Web Components only: no external dependencies or backend commands.
 * Dynamic values are inserted with textContent (never via HTML interpolation).
 */
const STATE_NAMES = {
  disarmed: "Disinserito", arming: "Inserimento in corso",
  armed_away: "Inserito", triggered: "ALLARME SCATTATO",
  pending: "In attesa", unavailable: "Non disponibile",
  unknown: "Sconosciuto"
};

class AdaptiveAlarmCard extends HTMLElement {
  setConfig(config) {
    if (!config || typeof config !== "object" || Array.isArray(config)) {
      throw new Error("Adaptive Alarm: nell'editor scheda usa 'type: custom:adaptive-alarm-card' SENZA il trattino iniziale.");
    }
    if (config.entity !== undefined && (
      typeof config.entity !== "string" ||
      !config.entity.startsWith("alarm_control_panel.")
    )) {
      throw new Error("Adaptive Alarm: entity deve essere alarm_control_panel.*");
    }
    this._config = config;
    if (!this.shadowRoot) this.attachShadow({mode: "open"});
    this._render();
  }

  set hass(value) {
    this._hass = value;
    this._render();
  }

  getCardSize() { return 7; }

  _add(parent, tag, cls, value) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (value !== undefined && value !== null) node.textContent = String(value);
    parent.appendChild(node);
    return node;
  }

  _findAlarm() {
    const states = this._hass?.states || {};
    if (this._config?.entity) return states[this._config.entity] || null;
    const matches = Object.values(states).filter((st) =>
      st.entity_id.startsWith("alarm_control_panel.") &&
      Array.isArray(st.attributes?.protected_zones) &&
      Array.isArray(st.attributes?.excluded_zones) &&
      Array.isArray(st.attributes?.pending_zones)
    );
    return matches[0] || null;
  }

  _findHealth() {
    const states = this._hass?.states || {};
    return Object.values(states).find((st) =>
      st.entity_id.startsWith("sensor.") &&
      typeof st.attributes?.protected_zone_problem_states === "object" &&
      Array.isArray(st.attributes?.active_zone_monitoring)
    ) || null;
  }

  _section(parent, title, zones, empty) {
    const outer = this._add(parent, "section", "section");
    const heading = this._add(outer, "div", "section-title");
    this._add(heading, "strong", "", title);
    this._add(heading, "span", "count", (zones || []).length);
    if (!(zones || []).length) {
      this._add(outer, "div", "empty", empty);
      return;
    }
    const grid = this._add(outer, "div", "zone-list");
    for (const id of zones) {
      const st = this._hass.states[id];
      const item = this._add(grid, "div", "zone");
      const indicator = this._add(item, "span", "dot");
      const state = st?.state ?? "unavailable";
      indicator.classList.add(
        state === "off" || state === "closed" ? "good" :
        state === "on" || state === "open" ? "bad" : "unknown"
      );
      const name = this._add(item, "span", "zone-name",
        st?.attributes?.friendly_name || id);
      name.title = id;
      this._add(item, "span", "zone-state",
        state === "off" ? "Chiuso" : state === "on" ? "Aperto" : state);
    }
  }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const root = this.shadowRoot;
    root.replaceChildren();
    const style = document.createElement("style");
    style.textContent = `
      :host {display:block; color:var(--primary-text-color);}
      ha-card {padding:18px 18px 12px; border-radius:var(--ha-card-border-radius,14px);}
      .head {display:flex; justify-content:space-between; align-items:center; gap:12px;}
      h2 {font-size:18px; margin:0; font-weight:650;}
      .subtitle {font-size:12px; color:var(--secondary-text-color); margin:4px 0 0;}
      .state {font-size:14px; font-weight:700; border-radius:12px; padding:7px 10px;
        background:var(--secondary-background-color); display:flex;
        align-items:center; gap:6px;}
      .alarm-state-icon {--mdc-icon-size:21px;flex-shrink:0;animation:none;}
      .alarm-state-icon.is-triggered {color:var(--error-color,#d33);
        animation:adaptive-alarm-triggered-flash 1.15s ease-in-out infinite;}
      @keyframes adaptive-alarm-triggered-flash {
        0%, 100% {opacity:1;}
        50% {opacity:.12;}
      }
      @media (prefers-reduced-motion:reduce) {
        .alarm-state-icon.is-triggered {animation:none;}
      }
      .state.armed {color:var(--success-color,#32a16d);}
      .state.alarm {color:var(--error-color,#d33); background:var(--secondary-background-color);}
      .state.disarmed {color:var(--secondary-text-color);}
      .stats {display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px;
        margin:17px 0 13px;}
      .stat {padding:10px; border-radius:10px; background:var(--secondary-background-color);}
      .stat strong {display:block; font-size:24px; line-height:1.25;}
      .stat span {font-size:11px; color:var(--secondary-text-color);}
      .section {border-top:1px solid var(--divider-color); padding:11px 0;}
      .section-title {display:flex; justify-content:space-between; margin-bottom:7px;
        gap:9px;}
      .section-title strong {font-size:13px;}
      .count {font-size:12px; color:var(--secondary-text-color);}
      .zone-list {display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:6px;}
      .zone {display:flex;align-items:center;gap:7px;border-radius:8px;
        padding:6px 8px; background:var(--secondary-background-color);}
      .zone-name {flex:1; min-width:0; overflow-wrap:anywhere; font-size:12px;}
      .zone-state {font-size:11px; color:var(--secondary-text-color);}
      .dot {width:8px;height:8px;border-radius:50%;flex-shrink:0;}
      .dot.good {background:var(--success-color,#32a16d);}
      .dot.bad {background:var(--error-color,#d33);}
      .dot.unknown {background:var(--warning-color,#e0a229);}
      .empty {font-size:12px;color:var(--secondary-text-color);}
      .detail {font-size:12px;margin:7px 0;color:var(--secondary-text-color);
        overflow-wrap:anywhere;}
      button {border:1px solid var(--divider-color);border-radius:10px;
        background:transparent;color:var(--primary-color);padding:7px 10px;
        font:inherit;cursor:pointer;}
      .bottom {display:flex;justify-content:flex-end;margin-top:7px;}
    `;
    root.appendChild(style);
    const card = this._add(root,"ha-card","");
    const alarm = this._findAlarm();
    if (!alarm) {
      this._add(card,"h2","","Adaptive Alarm");
      this._add(card,"p","empty","Pannello non trovato. Aggiungi 'entity: alarm_control_panel.nome' alla scheda.");
      return;
    }
    const attrs=alarm.attributes||{};
    const header=this._add(card,"div","head");
    const name=this._add(header,"div","");
    this._add(name,"h2","",this._config.title||"Adaptive Alarm");
    this._add(name,"div","subtitle","Riepilogo protezione in tempo reale");
    const status=this._add(header,"div","state");
    status.classList.add(alarm.state==="triggered"?"alarm":
      alarm.state==="armed_away"?"armed":"disarmed");
    const statusIcon=this._add(status,"ha-icon","alarm-state-icon");
    const icons={
      disarmed:"mdi:shield-off", arming:"mdi:shield-sync",
      armed_away:"mdi:shield-lock", triggered:"mdi:shield-alert",
    };
    statusIcon.setAttribute("icon",icons[alarm.state]||"mdi:shield-outline");
    // Do not animate arming or armed states; only a genuine alarm.
    if(alarm.state==="triggered")statusIcon.classList.add("is-triggered");
    this._add(status,"span","state-label",STATE_NAMES[alarm.state]||alarm.state);

    const protectedZones=attrs.protected_zones||[];
    const pendingZones=attrs.pending_zones||[];
    const excludedZones=attrs.excluded_zones||[];
    const stats=this._add(card,"div","stats");
    for(const [n,label] of [
      [protectedZones.length,"Protetti"],
      [pendingZones.length,"In attesa"],
      [excludedZones.length,"Esclusi"]
    ]){
      const stat=this._add(stats,"div","stat");
      this._add(stat,"strong","",n);
      this._add(stat,"span","",label);
    }

    this._section(card,"Contatti protetti",protectedZones,"Nessun contatto protetto");
    this._section(card,"Contatti in attesa",pendingZones,"Nessun contatto in attesa");
    this._section(card,"Contatti esclusi",excludedZones,"Nessun contatto escluso");

    const detail=this._add(card,"section","section");
    this._add(detail,"div","section-title").textContent="Diagnostica";
    const health=this._findHealth();
    const problemStates=health?.attributes?.protected_zone_problem_states || {};
    const lines=[
      ["Salute sensori", health?.state || "Non disponibile"],
      ["Contatti anomali", Object.keys(problemStates).length ?
        Object.entries(problemStates).map(([id, reason]) =>
          (this._hass.states[id]?.attributes?.friendly_name || id) + ": " + reason
        ).join("; ") : "Nessuno"],
      ["Requisiti attivi",(attrs.minimum_routes||[]).join(", ")||"—"],
      ["Ultima causa",attrs.trigger_cause||"—"],
      ["Problema",attrs.fault||"Nessuno"],
      ["Sirena",attrs.siren_entity ?
        (attrs.siren_enabled?"Abilitata":"Disabilitata")+
        " · "+(this._hass.states[attrs.siren_entity]?.state||"Non disponibile") :
        "Non configurata"],
    ];
    if(attrs.siren_last_error)lines.push(["Errore sirena",attrs.siren_last_error]);
    for(const [label,value] of lines){
      const line=this._add(detail,"div","detail");
      this._add(line,"strong","",label+": ");
      this._add(line,"span","",value);
    }

    const footer=this._add(card,"div","bottom");
    const link=this._add(footer,"button","","Dettagli allarme");
    link.type="button";
    link.addEventListener("click",()=>{
      this.dispatchEvent(new CustomEvent("hass-more-info",{
        detail:{entityId:alarm.entity_id},bubbles:true,composed:true
      }));
    });
  }
}

// Home Assistant's scoped custom-element registry may replace the native
// registry AFTER a very early frontend extra-module has already run.
// In that race the JS executes but HA reports "Custom element doesn't exist".
// Register immediately, then re-check once the HA root has initialized.
// https://github.com/home-assistant/frontend/issues/53890
function registerAdaptiveAlarmCard() {
  if (!customElements.get("adaptive-alarm-card")) {
    customElements.define("adaptive-alarm-card", AdaptiveAlarmCard);
  }
}
registerAdaptiveAlarmCard();
if (typeof window.setInterval === "function") {
  let checks = 0;
  const checkHandle = window.setInterval(() => {
    checks += 1;
    if (!customElements.get("home-assistant") && checks < 600) return;
    window.clearInterval(checkHandle);
    registerAdaptiveAlarmCard();
  }, 100);
}
window.customCards=window.customCards||[];
if(!window.customCards.some(x=>x.type==="adaptive-alarm-card"))
  window.customCards.push({type:"adaptive-alarm-card",name:"Adaptive Alarm",
    description:"Stato, protetti, in attesa, esclusi e diagnostica"});
