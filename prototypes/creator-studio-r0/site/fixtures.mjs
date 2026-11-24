export const nav = [
 ['mission','Mission Control','◈'], ['create','Universal Create','✦'], ['batch','Batch Studio','▤'],
 ['library','Video Library','▣'], ['creative','Creative Library','❋'], ['review','Review Studio','◉'], ['operations','Operations & Agents','↳'],
];
const topics = ['Nearest-neighbor map','Equal loss, unequal gains','How canal locks lift boats','Monsoon vocabulary','The coral nursery','Solar eclipse geometry','Paper to paperback','How microphones listen','The city at low tide','A map of local trains','Why sourdough rises','The bicycle gear','A podcast recap','The history of a postage stamp','How bees navigate','The archive restoration','A lyric video','A missing voice model','An illustrated budget','The night shift'];
export function initial() {
  return {
    jobs: [
      { id:'fixture-canal', title:'How canal locks lift boats', art:'lock', format:'Long-form · 16:9', language:'English', track:'Track B', execution:'Rendered', qa:'Pass', creative:'Changes requested', eligible:true, attempts:['01 · Rendered fixture'], specRevision:'r2', pinnedAssets:['fixture-logo-a'] },
      { id:'fixture-map', title:'Nearest-neighbor map', art:'map', format:'Shorts · 9:16', language:'English', track:'Track A', execution:'Failed', qa:'Fail', creative:'Accepted', eligible:false, attempts:['01 · Align failed: fixture word timing missing'], specRevision:'r1', pinnedAssets:[] },
      { id:'fixture-gain', title:'Equal loss, unequal gains', art:'gain', format:'Shorts · 9:16', language:'English', track:'Track A', execution:'Rendered', qa:'Pass', creative:'Not requested', eligible:true, attempts:['01 · Rendered fixture'], specRevision:'r1', pinnedAssets:[] },
    ],
    rows: topics.map((title,i) => ({ id:`fixture-row-${i+1}`, title, revision:'r1', format:i%3===2?'Long-form':'Shorts', language:i%4===3?'Hindi':'English', state:i<12?'Ready':i<15?'Invalid':i<17?'Blocked':i===17?'Duplicate':i===18?'Stale':'Running', issue:i<12?'':i<15?'Missing production detail':i===15?'Manual Track B handoff':i===16?'Lyric workflow is planned':i===17?'Matches an existing row':i===18?'Capability evidence expired':'Existing attempt active' })),
    episodes: Array.from({length:20},(_,i)=>({id:`fixture-episode-${i+1}`, title:['The lower gate','Reading waterlines','Inside the chamber','नहर का सफ़र','The missing voice'][i] ?? `Waterways / Episode ${i+1}`, revision:i===0||i===3?'r2':'r3', status:i===0?'Reviewed':i===4||i===1?'Blocked':'Draft', language:i===3?'Hindi · overridden':'English · inherited', voice:i===4?'None · explicitly cleared':'Narrator · inherited', asset:[0,1,3].includes(i)?'fixture-logo-a':'fixture-logo-b'})),
    assets:[{id:'fixture-logo-a',name:'Series logo / first cut',digest:'fixture-digest-a',kind:'SVG illustration',rights:'Original fixture',availability:'Missing for new drafts'}, {id:'fixture-logo-b',name:'Series logo / revised',digest:'fixture-digest-b',kind:'SVG illustration',rights:'Original fixture',availability:'Ready in fixtures'}],
    activity:[['14:22','Storyboard handoff returned','fixture-canal'],['14:19','Alignment evidence missing','fixture-map'],['14:05','Creative brief filed','fixture-gain']],
    revision:1, gate:'Composition', grants:{}, selected:new Set(), exports:new Set(), exportSelection:new Set(['fixture-canal','fixture-map','fixture-gain']), filters:{},
    format:'Shorts · 9:16', source:'Topic', title:'A map of the night sky', detail:'', checked:false, frame:1,
  };
}
const art = {
 lock: `<rect width="640" height="330" fill="#bcb1e6"/><circle cx="500" cy="66" r="50" fill="#f7d89f"/><path d="M0 160H228V234H410V132H640V330H0Z" fill="#233344"/><path d="M0 179H228V251H410V151H640V330H0Z" fill="#438479"/><path d="M0 200H228M238 270H408M420 174H640" stroke="#a8e1cc" stroke-width="3" stroke-dasharray="10 8"/><path d="M228 137V270M410 114V270" stroke="#f8e5b5" stroke-width="8"/><path d="M284 234H355L340 250H299Z" fill="#fdcb8f"/><path d="M320 201V234L345 227Z" fill="#f8e5b5"/><path d="M466 214V180M455 192L466 180L477 192" fill="none" stroke="#f8e5b5" stroke-width="3"/>`,
 map:`<rect width="640" height="330" fill="#d5c6f2"/><path d="M0 82H640M0 165H640M0 248H640M160 0V330M320 0V330M480 0V330" stroke="#b09bcf"/><circle cx="308" cy="174" r="100" fill="none" stroke="#35275e" stroke-dasharray="7 7" stroke-width="3"/><path d="M308 174L395 125" stroke="#35275e" stroke-width="4"/><circle cx="308" cy="174" r="13" fill="#35275e"/><g fill="#704995"><circle cx="395" cy="125" r="11"/><circle cx="162" cy="91" r="11"/><circle cx="526" cy="218" r="11"/><circle cx="185" cy="258" r="11"/></g>`,
 gain:`<rect width="640" height="330" fill="#f3ca9f"/><path d="M85 271H564M85 72V271" stroke="#56414c" stroke-width="3"/><rect x="130" y="86" width="90" height="185" fill="#51436f"/><rect x="275" y="179" width="90" height="92" fill="#bc6655"/><rect x="420" y="132" width="90" height="139" fill="#547063"/><path d="M220 86H420M220 179H420" stroke="#715457" stroke-dasharray="6 7" stroke-width="2"/>`,
};
export const poster = (kind) => `<svg viewBox="0 0 640 330" aria-hidden="true" focusable="false">${art[kind] ?? art.map}</svg>`;
export function storyboard(frame) {
  const y = [248,207,153][frame], x = [115,311,502][frame];
  return `<svg viewBox="0 0 640 330" aria-hidden="true" focusable="false"><rect width="640" height="330" fill="#bcb1e6"/><circle cx="500" cy="62" r="44" fill="#f7d89f"/><path d="M0 248H228V${y}H410V153H640V330H0Z" fill="#438479"/><path d="M0 280H640V330H0Z" fill="#233344"/><path d="M228 ${frame===0?275:122}V280M410 ${frame===2?274:114}V280" stroke="#f8e5b5" stroke-width="9"/><path transform="translate(${x} ${y})" d="M-36 -2H39L25 14H-22ZM0 -4V-38L27 -12Z" fill="#f7d89f"/><path d="M5 261H208M244 ${y+14}H394M432 167H635" stroke="#b0e4d0" stroke-width="3" stroke-dasharray="8 8"/></svg>`;
}
