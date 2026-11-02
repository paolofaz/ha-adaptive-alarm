// Minimal DOM compatibility test; no network or browser.
const assert = require("node:assert/strict");
class FakeElement {
  constructor(tag="root") {
    this.tagName=tag;this.children=[];this._text="";this.className="";
    this.classList={add:(name)=>{this.className+=" "+name;}};
    this.listeners={};this.shadowRoot=null;
  }
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>c.textContent).join("");}
  appendChild(el){this.children.push(el);return el;}
  setAttribute(name,value){this.attributes??={};this.attributes[name]=String(value);}
  replaceChildren(...nodes){this.children=nodes;}
  addEventListener(name,fn){this.listeners[name]=fn;}
  attachShadow(){this.shadowRoot=new FakeElement("shadow");return this.shadowRoot;}
  dispatchEvent(){}
}
global.HTMLElement=FakeElement;
global.document={createElement:(tag)=>new FakeElement(tag)};
const registered=new Map();
global.customElements={
  define:(name,cls)=>registered.set(name,cls),
  get:(name)=>registered.get(name),
};
global.window={customCards:[]};
require("../custom_components/adaptive_alarm/www/adaptive-alarm-card.js");
const Card=registered.get("adaptive-alarm-card");
assert.ok(Card);
const card=new Card();
card.setConfig({title:"Antifurto"});
card.hass={states:{
  "alarm_control_panel.adaptive_alarm":{
    entity_id:"alarm_control_panel.adaptive_alarm",state:"armed_away",
    attributes:{protected_zones:["binary_sensor.finestra"],pending_zones:[],
      excluded_zones:["binary_sensor.persiana"], minimum_routes:["Sala"],
      siren_entity:"siren.casa",siren_enabled:true},
  },
  "binary_sensor.finestra":{
    entity_id:"binary_sensor.finestra",state:"off",
    attributes:{friendly_name:"Finestra Sala"},
  },
  "binary_sensor.persiana":{
    entity_id:"binary_sensor.persiana",state:"on",
    attributes:{friendly_name:"Persiana Sala"},
  },
  "siren.casa":{entity_id:"siren.casa",state:"off",attributes:{}},
  "sensor.adaptive_health":{
    entity_id:"sensor.adaptive_health",state:"degraded",
    attributes:{protected_zone_problem_states:{
      "binary_sensor.finestra":"unavailable",
    },active_zone_monitoring:["binary_sensor.finestra"]},
  },
}};
const rendered=card.shadowRoot.textContent;
for(const text of ["Antifurto","Inserito","Finestra Sala","Persiana Sala",
  "Protetti","Esclusi","Salute sensori","degraded","Contatti anomali",
  "unavailable","Sirena"]){
  assert.ok(rendered.includes(text), "Missing: "+text);
}
const stateIcon=card.shadowRoot.children[1].children[0].children[1].children[0];
assert.equal(stateIcon.tagName,"ha-icon");
assert.equal(stateIcon.attributes.icon,"mdi:shield-lock");
assert.ok(!stateIcon.className.includes("is-triggered"));
for(const [state,expectedIcon,animated] of [
  ["disarmed","mdi:shield-off",false],
  ["arming","mdi:shield-sync",false],
  ["armed_away","mdi:shield-lock",false],
  ["triggered","mdi:shield-alert",true],
]){
  card.hass={
    states:{...card._hass.states,
      "alarm_control_panel.adaptive_alarm":{
        ...card._hass.states["alarm_control_panel.adaptive_alarm"],state
      }},
  };
  const icon=card.shadowRoot.children[1].children[0].children[1].children[0];
  assert.equal(icon.attributes.icon,expectedIcon);
  assert.equal(icon.className.includes("is-triggered"),animated);
}
assert.equal(window.customCards.length,1);
const second=new Card();
second.setConfig({entity:"alarm_control_panel.adaptive_alarm"});
second.hass=card._hass;
assert.ok(second.shadowRoot.textContent.includes("Inserito"));
assert.throws(()=>second.setConfig({entity:"switch.unsafe"}), /alarm_control_panel/);
console.log("Adaptive Alarm Lovelace card: runtime and health rendering OK");
