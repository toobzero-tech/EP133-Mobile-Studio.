import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export function start(){
 const canvas=document.querySelector("#stage"),scene=new THREE.Scene();
 scene.background=null; // Paper-only scene, no environmental backdrop.
 let travelDistance=0;
 const rawPathZ=x=>1.35*Math.sin(x*.052)+.48*Math.sin(x*.117+.6);
 // Advance the curve profile beneath the fixed runner for endless forward travel.
 const pathZ=x=>rawPathZ(x+travelDistance)-rawPathZ(-2.25+travelDistance);
 const camera=new THREE.PerspectiveCamera(54,1,.1,140);camera.position.set(-10,3.35,0);camera.lookAt(5.5,1.05,0);
 const renderer=new THREE.WebGLRenderer({canvas,antialias:false,alpha:false,powerPreference:"high-performance"});renderer.setPixelRatio(Math.min(devicePixelRatio,1.2));renderer.shadowMap.enabled=false;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
 scene.add(new THREE.HemisphereLight(0xffffff,0xb8b2a8,2.2));
 const sun=new THREE.DirectionalLight(0xffffff,1.15);sun.position.set(-5,10,7);scene.add(sun);
 const grayColor=color=>{const c=new THREE.Color(color);const y=.299*c.r+.587*c.g+.114*c.b;return new THREE.Color().setRGB(y,y,y)};
 const mat=(color,roughness=.94,metalness=0)=>new THREE.MeshStandardMaterial({color:grayColor(color),map:graphiteTexture,roughness,metalness});
 function addSketchOutlines(root){
  root.traverse(o=>{if(!o.isMesh||o.userData.sketchOutline)return;o.userData.sketchOutline=true;
   const edges=new THREE.EdgesGeometry(o.geometry,18);
   const ink=new THREE.LineBasicMaterial({color:0x37332e,transparent:true,opacity:.68,depthWrite:false});
   const lines=new THREE.LineSegments(edges,ink);lines.renderOrder=2;o.add(lines);
  });
 }
 function makePaperTexture(){
  const c=document.createElement("canvas");c.width=c.height=512;const ctx=c.getContext("2d");
  ctx.fillStyle="#faf9f6";ctx.fillRect(0,0,512,512);
  for(let i=0;i<32;i++){const x=Math.random()*512,y=Math.random()*512;const g=ctx.createLinearGradient(x-35,y-20,x+45,y+30);g.addColorStop(0,"rgba(90,85,78,.015)");g.addColorStop(.5,"rgba(255,255,255,.28)");g.addColorStop(1,"rgba(80,74,68,.045)");ctx.strokeStyle=g;ctx.lineWidth=1+Math.random()*3;ctx.beginPath();ctx.moveTo(x-35,y-20);ctx.quadraticCurveTo(x+5,y+35,x+45,y+30);ctx.stroke()}
  for(let i=0;i<11000;i++){const x=Math.random()*512,y=Math.random()*512,a=.025+Math.random()*.07;ctx.fillStyle="rgba(55,49,42,"+a+")";ctx.fillRect(x,y,Math.random()*1.5+.3,.5)}
  ctx.strokeStyle="rgba(65,59,51,.10)";ctx.lineWidth=.6;
  for(let i=0;i<95;i++){const x=Math.random()*512,y=Math.random()*512;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+5+Math.random()*24,y-2+Math.random()*4);ctx.stroke()}
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(18,18);t.colorSpace=THREE.SRGBColorSpace;return t;
 }
 const paperTexture=makePaperTexture();
 function makeGraphiteTexture(){
  const c=document.createElement("canvas");c.width=c.height=256;const ctx=c.getContext("2d");
  ctx.fillStyle="#eeeae3";ctx.fillRect(0,0,256,256);
  // Layered, irregular graphite strokes imitate pencil pressure and cross-hatching.
  const angles=[-.78,-.28,.32,.82];
  for(let pass=0;pass<angles.length;pass++){
   const angle=angles[pass],density=pass<2?240:145;
   ctx.strokeStyle=pass===0?"rgba(28,27,26,.19)":pass===1?"rgba(38,36,33,.13)":"rgba(42,39,35,.085)";
   ctx.lineCap="round";
   for(let i=0;i<density;i++){
    const x=Math.random()*320-32,y=Math.random()*320-32,len=3+Math.random()*(pass<2?24:15);
    const a=angle+(Math.random()-.5)*.22;
    ctx.lineWidth=.25+Math.random()*(pass===0?.85:.5);
    ctx.beginPath();ctx.moveTo(x,y);
    ctx.lineTo(x+Math.cos(a)*len,y+Math.sin(a)*len);ctx.stroke();
   }
  }
  for(let i=0;i<1800;i++){
   const x=Math.random()*256,y=Math.random()*256;
   ctx.fillStyle="rgba(24,23,22,"+(Math.random()*.16)+")";
   ctx.fillRect(x,y,.35+Math.random()*.85,.35+Math.random()*.65);
  }
  // Uneven pressure patches create the soft, rubbed graphite look.
  for(let i=0;i<24;i++){
   const x=Math.random()*256,y=Math.random()*256,r=4+Math.random()*19;
   const g=ctx.createRadialGradient(x,y,0,x,y,r);
   g.addColorStop(0,"rgba(45,42,38,.09)");g.addColorStop(1,"rgba(45,42,38,0)");
   ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
  }
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(2.5,2.5);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=1;return t;
 }
 const graphiteTexture=makeGraphiteTexture();
 const lineMat=mat(0x777064),wood=mat(0xc99a55),graphite=mat(0x302d29),eraser=mat(0xb97875),paper=mat(0xe5ddce);
 // The paper sheet is the complete backdrop. No floor, road, borders or scenery.
 paperTexture.wrapS=paperTexture.wrapT=THREE.ClampToEdgeWrapping;
 paperTexture.repeat.set(1,1);
 scene.background=paperTexture;
 function updateTrack(){ /* Logical path only; intentionally no visible track. */ }
 const runner=new THREE.Group();runner.position.set(-2.25,0,0);scene.add(runner);
 let mixer=null,runAction=null,modelReady=false;
 function fallbackRunner(){
  const skin=mat(0xc69d7d),shirt=mat(0x555b5c),pants=mat(0x34383a),shoe=mat(0x252525);
  const sphere=(r,m,x,y,z)=>{const o=new THREE.Mesh(new THREE.SphereGeometry(r,20,16),m);o.position.set(x,y,z);runner.add(o);return o};
  const torso=new THREE.Mesh(new THREE.CapsuleGeometry(.29,.62,6,12),shirt);torso.position.y=1.12;runner.add(torso);
  sphere(.19,skin,0,1.78,0);
  const limbs=[];
  for(let side of [-1,1]){
   let leg=new THREE.Mesh(new THREE.CapsuleGeometry(.105,.53,5,10),pants);leg.position.set(side*.14,.48,0);runner.add(leg);
   let arm=new THREE.Mesh(new THREE.CapsuleGeometry(.075,.5,5,10),skin);arm.position.set(side*.34,1.18,0);runner.add(arm);
   let foot=new THREE.Mesh(new THREE.BoxGeometry(.2,.12,.36),shoe);foot.position.set(side*.14,.08,.09);runner.add(foot);
   limbs.push({leg,arm,foot,side});
  }
  runner.userData.limbs=limbs;
 }
 fallbackRunner();addSketchOutlines(runner);runner.userData.ownedMaterials=[];
 const loader=new GLTFLoader();
 loader.load("./runner.glb",g=>{
  const oldGeometry=new Set(),oldMaterials=new Set();
  runner.traverse(o=>{if(o.geometry)oldGeometry.add(o.geometry);for(const m of (Array.isArray(o.material)?o.material:[o.material]))if(m)oldMaterials.add(m)});
  while(runner.children.length)runner.remove(runner.children[0]);
  oldGeometry.forEach(v=>v.dispose());oldMaterials.forEach(v=>v.dispose());
  runner.userData.limbs=null;
  const model=g.scene;const box=new THREE.Box3().setFromObject(model),size=box.getSize(new THREE.Vector3());const scale=1.78/Math.max(size.y,.01);model.scale.setScalar(scale);const b2=new THREE.Box3().setFromObject(model);model.position.y-=b2.min.y;model.traverse(o=>{if(o.isMesh){
   const source=Array.isArray(o.material)?o.material:[o.material];
   const pencilMats=source.map(m=>{
    const color=grayColor(m?.color??0x777777);
    if(m){
     for(const key of ["map","normalMap","roughnessMap","metalnessMap","emissiveMap","aoMap","alphaMap","bumpMap","displacementMap"])if(m[key])m[key].dispose();
     m.dispose();
    }
    return new THREE.MeshStandardMaterial({color,map:graphiteTexture,roughness:1,metalness:0});
   });
   o.material=Array.isArray(o.material)?pencilMats:pencilMats[0];
  }});runner.add(model);addSketchOutlines(model);model.userData.ownedMaterials=[];addGraphiteHatching(model,0x13a5);
  runner.userData.model=model;runner.userData.modelBaseY=model.position.y;
  if(g.animations.length){mixer=new THREE.AnimationMixer(model);const clip=g.animations.find(a=>/run|jog|sprint/i.test(a.name))||g.animations[0];runAction=mixer.clipAction(clip);runAction.play()}
  modelReady=true;
 },undefined,error=>{console.error("Runner model failed to load; using procedural runner",error);});
 const obstacles=[];let nextSpawn=1.2,elapsed=0,score=0,best=0,speed=5,paused=true,dead=false,jumpY=0,jumpV=0,grounded=true,skill=.3,streak=0,view=0,laneZ=0,targetLaneZ=0;
 try{best=+(localStorage.getItem("rm3dBest")||0)}catch(e){best=0}
 let audio=null,soundEnabled=true,lastStep=0;
 function audioReady(){if(!soundEnabled)return null;try{if(!audio){const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return null;audio=new AC()}if(audio.state==="suspended")audio.resume();return audio}catch(e){return null}}
 function tone(freq,duration=.09,type="sine",volume=.045,slide=0){const ctx=audioReady();if(!ctx)return;const osc=ctx.createOscillator(),gain=ctx.createGain();osc.type=type;osc.frequency.setValueAtTime(freq,ctx.currentTime);if(slide)osc.frequency.exponentialRampToValueAtTime(Math.max(30,freq+slide),ctx.currentTime+duration);gain.gain.setValueAtTime(.0001,ctx.currentTime);gain.gain.exponentialRampToValueAtTime(volume,ctx.currentTime+.012);gain.gain.exponentialRampToValueAtTime(.0001,ctx.currentTime+duration);osc.connect(gain);gain.connect(ctx.destination);osc.start();osc.stop(ctx.currentTime+duration+.02)}
 function impactSound(){tone(115,.16,"triangle",.065,-65);tone(62,.22,"sine",.045,-28)}

 function pencil(x,z,h=1.0){
  const group=new THREE.Group();group.position.set(x,0,pathZ(x)+z);
  const body=new THREE.Mesh(new THREE.CylinderGeometry(.075,.075,h-.18,12),wood);body.position.y=(h-.18)/2+.09;group.add(body);
  const tip=new THREE.Mesh(new THREE.ConeGeometry(.075,.18,12),wood);tip.position.y=h-.09;group.add(tip);
  const lead=new THREE.Mesh(new THREE.ConeGeometry(.025,.055,8),graphite);lead.position.y=h+.025;group.add(lead);
  const band=new THREE.Mesh(new THREE.CylinderGeometry(.078,.078,.07,12),eraser);band.position.y=.07;group.add(band);
  const rings=new THREE.Mesh(new THREE.CylinderGeometry(.079,.079,.018,12),mat(0xb9a88f,.45,.4));rings.position.y=.115;group.add(rings);
  scene.add(group);addSketchOutlines(group);obstacles.push({mesh:group,x,z,w:.42,h,type:"pencil",passed:false});
 }
 function boxObstacle(x,z,w,h,depth,color,type){
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,depth),mat(color));mesh.position.set(x,h/2,pathZ(x)+z);scene.add(mesh);addSketchOutlines(mesh);obstacles.push({mesh,x,z,w,h,type,passed:false});
 }
 function addGraphiteHatching(root,seed=1){
  // Draw separate, irregular graphite strokes on each mesh's camera-facing
  // surface. This follows the runner's limbs and clothing instead of laying
  // one flat hatch sheet across the entire character.
  let state=(seed>>>0)||1;
  const rand=()=>{state^=state<<13;state^=state>>>17;state^=state<<5;return (state>>>0)/4294967296};
  const ink=new THREE.LineBasicMaterial({color:0x393632,transparent:true,opacity:.19,depthWrite:false});
  let meshIndex=0;
  root.traverse(mesh=>{
   if(!mesh.isMesh||!mesh.geometry)return;
   const geometry=mesh.geometry;
   if(!geometry.boundingBox)geometry.computeBoundingBox();
   const bounds=geometry.boundingBox;
   if(!bounds||!Number.isFinite(bounds.min.x)||!Number.isFinite(bounds.max.y))return;
   const width=bounds.max.z-bounds.min.z,height=bounds.max.y-bounds.min.y;
   if(width<.025||height<.025)return;
   const front=bounds.min.x-.003;
   const pts=[];
   const count=Math.min(15,5+Math.floor(rand()*8));
   for(let i=0;i<count;i++){
    const y=bounds.min.y+rand()*height,z=bounds.min.z+rand()*width;
    const len=Math.min(width*.28,.025+rand()*.085),dy=(rand()-.5)*Math.min(height*.06,.018);
    pts.push(front,y,z,front,y+dy,z+len);
   }
   for(let i=0;i<Math.floor(count*.45);i++){
    const y=bounds.min.y+rand()*height,z=bounds.min.z+rand()*width;
    const len=Math.min(height*.22,.025+rand()*.07);
    pts.push(front,y,z,front,y+len,z-len*.35);
   }
   const hatchGeometry=new THREE.BufferGeometry();
   hatchGeometry.setAttribute("position",new THREE.Float32BufferAttribute(pts,3));
   const strokes=new THREE.LineSegments(hatchGeometry,ink);
   strokes.renderOrder=3;
   mesh.add(strokes);
   meshIndex++;
  });
  if(root.userData.ownedMaterials)root.userData.ownedMaterials.push(ink);
 }
 function obstacleShape(x,z,type,variant=0){
  const variationSeed=variant;
  const group=new THREE.Group();group.position.set(x,0,pathZ(x)+z);scene.add(group);
  const variation=variationSeed%100;
  const sx=.84+((variation*37)%31)/100,sy=.86+((variation*17)%29)/100,sz=.84+((variation*13)%23)/100;
  group.scale.set(sx,sy,sz);group.rotation.y=(((variation*19)%17)-8)*.018;
  const woodMat=mat(0xaaa49a),darkMat=mat(0x66615b),stoneMat=mat(0x858078),paperMat=mat(0xd2ccc0);
  let w=1,h=.7,depth=.7;
  group.userData.ownedMaterials=[woodMat,darkMat,stoneMat,paperMat];
  const add=(geo,m,px,py,pz,rot=0)=>{const o=new THREE.Mesh(geo,m);o.position.set(px,py,pz);o.rotation.z=rot;group.add(o);return o};
  if(type==="branch"){
    w=1.4+variation*.08;h=.48;depth=.5;
    add(new THREE.CylinderGeometry(.09,.14,w,9),woodMat,0,.25,0,Math.PI/2);
    for(let k=0;k<2+variation%3;k++){const zoff=(k-1)*.23;add(new THREE.CylinderGeometry(.035,.07,.45,7),woodMat,.1,.48,zoff,Math.PI/3+(k%2)*.3)}
  }else if(type==="log"){
    w=1.5+variation*.1;h=.42;depth=.62;
    add(new THREE.CylinderGeometry(.23,.24,w,10),woodMat,0,.23,0,Math.PI/2);
    add(new THREE.CircleGeometry(.23,10),darkMat,w/2,.23,0,0);add(new THREE.CircleGeometry(.23,10),darkMat,-w/2,.23,0,0);
  }else if(type==="rock"){
    w=.65+variation*.12;h=.5+variation*.06;depth=.65;
    add(new THREE.DodecahedronGeometry(.42+variation*.06,0),stoneMat,0,h*.45,0);
  }else if(type==="crate"){
    w=.72;h=.72;depth=.72;add(new THREE.BoxGeometry(w,h,depth),woodMat,0,h/2,0);
    for(let a=-1;a<=1;a+=2){add(new THREE.BoxGeometry(.08,h+.05,.78),darkMat,a*.27,h/2,0);add(new THREE.BoxGeometry(.78,.08,.08),darkMat,0,h/2+a*.27,0)}
  }else if(type==="barrier"){
    w=1.8;h=.62;depth=.28;add(new THREE.BoxGeometry(w,h,depth),paperMat,0,h/2,0);
    for(let a=-1;a<=1;a+=.5)add(new THREE.BoxGeometry(.1,h+.04,.32),darkMat,a*.65,h/2,0);
  }else if(type==="stump"){
    w=.65;h=.55;depth=.65;add(new THREE.CylinderGeometry(.25,.34,h,9),woodMat,0,h/2,0);
    add(new THREE.CylinderGeometry(.26,.26,.06,9),paperMat,0,h+.02,0);
  }else if(type==="bucket"){
    w=.55;h=.65;depth=.55;add(new THREE.CylinderGeometry(.22,.3,h,10),darkMat,0,h/2,0);
    add(new THREE.TorusGeometry(.26,.035,6,12),woodMat,0,h,0);
  }else if(type==="cone"){
    w=.45;h=.75;depth=.45;add(new THREE.ConeGeometry(.22,h,8),darkMat,0,h/2,0);add(new THREE.BoxGeometry(.52,.08,.52),paperMat,0,.04,0);
  }else if(type==="pencil"){
    w=.42;h=.9+variation*.08;depth=.42;
    const body=new THREE.Mesh(new THREE.CylinderGeometry(.075,.075,h-.18,10),wood);body.position.y=(h-.18)/2+.09;group.add(body);
    add(new THREE.ConeGeometry(.075,.18,10),wood,0,h-.09,0);add(new THREE.ConeGeometry(.025,.055,8),graphite,0,h+.025,0);
    add(new THREE.CylinderGeometry(.078,.078,.07,10),eraser,0,.07,0);
  }else if(type==="books"){
    w=.85;h=.6;depth=.65;for(let i=0;i<2+variation%2;i++)add(new THREE.BoxGeometry(w,.24,depth),paperMat,0,.12+i*.25,0,(variation%2)*.06);
  }else if(type==="rubble"){
    w=.95;h=.38;depth=.7;for(let i=0;i<3;i++)add(new THREE.DodecahedronGeometry(.2+((variation+i)%3)*.05,0),stoneMat,(i-1)*.22,.18,(i%2)*.18);
  }else if(type==="chair"){
    w=.9;h=1.05;depth=.72;add(new THREE.BoxGeometry(.72,.09,.68),woodMat,0,.48,0);add(new THREE.BoxGeometry(.72,.62,.09),woodMat,0,.83,-.29);
    for(let a of [-1,1])for(let b of [-1,1])add(new THREE.BoxGeometry(.07,.48,.07),darkMat,a*.29,.24,b*.25);
  }else if(type==="umbrella"){
    w=1.05;h=1.12;depth=.9;add(new THREE.CylinderGeometry(.025,.025,.9,7),darkMat,0,.48,0);add(new THREE.SphereGeometry(.52,12,7,0,Math.PI*2,0,Math.PI/2),paperMat,0,.96,0);
    for(let a=0;a<6;a++){const t=a*Math.PI/3;add(new THREE.CylinderGeometry(.012,.012,.72,5),darkMat,Math.cos(t)*.22,.78,Math.sin(t)*.22,Math.PI/2)}
  }else if(type==="ladder"){
    w=.9;h=1.25;depth=.35;for(let a of [-1,1])add(new THREE.BoxGeometry(.07,h,.07),woodMat,a*.36,h/2,0);for(let y=.18;y<h;y+=.22)add(new THREE.BoxGeometry(.78,.055,.07),darkMat,0,y,0);
  }else if(type==="wheel"){
    w=.95;h=.95;depth=.3;const tire=add(new THREE.TorusGeometry(.39,.12,8,18),darkMat,0,.48,0);tire.rotation.y=Math.PI/2;const hub=add(new THREE.CylinderGeometry(.14,.14,.34,12),paperMat,0,.48,0);hub.rotation.z=Math.PI/2;
    for(let a=0;a<8;a++){const t=a*Math.PI/4;add(new THREE.BoxGeometry(.035,.62,.035),woodMat,Math.sin(t)*.2,.48+Math.cos(t)*.2,0,t)}
  }else if(type==="suitcase"){
    w=.92;h=.62;depth=.58;add(new THREE.BoxGeometry(w,h,depth),darkMat,0,h/2,0);add(new THREE.BoxGeometry(.34,.08,.06),woodMat,0,h+.04,0);for(let a of [-1,1])add(new THREE.BoxGeometry(.05,.12,.06),paperMat,a*.31,.03,.25);
  }else if(type==="lamp"){
    w=.72;h=1.18;depth=.72;add(new THREE.CylinderGeometry(.22,.25,.07,12),darkMat,0,.04,0);add(new THREE.CylinderGeometry(.035,.045,.72,8),woodMat,0,.42,0);add(new THREE.ConeGeometry(.34,.38,12),paperMat,0,.98,0);
  }else if(type==="hoop"){
    w=1.1;h=.92;depth=.32;const ring=add(new THREE.TorusGeometry(.36,.075,8,20),woodMat,0,.5,0);ring.rotation.y=Math.PI/2;for(let a of [-1,1])add(new THREE.BoxGeometry(.07,.9,.07),darkMat,a*.42,.45,0);add(new THREE.BoxGeometry(.95,.07,.07),darkMat,0,.05,0);
  }else if(type==="cans"){
    w=.88;h=.62;depth=.48;for(let a=-1;a<=1;a++)add(new THREE.CylinderGeometry(.13,.13,.48,10),variation%2?woodMat:darkMat,a*.27,.24,(a%2)*.12);add(new THREE.CylinderGeometry(.12,.12,.035,10),paperMat,0,.5,0);
  }else if(type==="newspaper"){
    w=1.25;h=.18;depth=.86;add(new THREE.BoxGeometry(w,.045,depth),paperMat,0,.06,0,(variation%7-3)*.045);for(let a=0;a<5;a++)add(new THREE.BoxGeometry(.16,.008,.018),darkMat,-.42+a*.2,.088,(a%2)*.2-.1);
  }else if(type==="sign"){
    w=.78;h=1.05;depth=.18;add(new THREE.BoxGeometry(.68,.58,.07),paperMat,0,.72,0);add(new THREE.CylinderGeometry(.035,.045,.72,7),darkMat,0,.36,0);add(new THREE.BoxGeometry(.82,.06,.24),woodMat,0,.04,0);
  }else if(type==="backpack"){
    w=.72;h=.82;depth=.48;add(new THREE.BoxGeometry(w,h,depth),darkMat,0,h/2,0);
    add(new THREE.BoxGeometry(.5,.36,.08),paperMat,0,.58,.25);add(new THREE.TorusGeometry(.15,.035,6,12),woodMat,0,h+.03,0);
  }else if(type==="helmet"){
    w=.72;h=.55;depth=.72;add(new THREE.SphereGeometry(.34,12,8,0,Math.PI*2,0,Math.PI/2),paperMat,0,.28,0);
    add(new THREE.BoxGeometry(.72,.09,.48),darkMat,0,.12,0);
  }else if(type==="skateboard"){
    w=1.35;h=.2;depth=.48;add(new THREE.BoxGeometry(w,.09,depth),woodMat,0,.13,0);
    for(let a of [-1,1])for(let b of [-1,1])add(new THREE.CylinderGeometry(.075,.075,.06,10),darkMat,a*.43,.055,b*.19,Math.PI/2);
  }else if(type==="ball"){
    w=.62;h=.62;depth=.62;add(new THREE.SphereGeometry(.3,12,10),paperMat,0,.31,0);
    for(let a=0;a<3;a++){const seam=add(new THREE.TorusGeometry(.22,.012,5,16),darkMat,0,.31,0);seam.rotation.set(a*.8,a*1.1,a*.55)}
  }else if(type==="bottle"){
    w=.34;h=.82;depth=.34;add(new THREE.CylinderGeometry(.15,.18,.58,10),paperMat,0,.31,0);
    add(new THREE.CylinderGeometry(.075,.09,.18,9),darkMat,0,.69,0);add(new THREE.CylinderGeometry(.07,.07,.07,8),woodMat,0,.815,0);
  }else if(type==="bin"){
    w=.72;h=.82;depth=.68;add(new THREE.BoxGeometry(w,h,depth),darkMat,0,h/2,0);
    add(new THREE.BoxGeometry(.82,.09,.76),woodMat,0,h+.035,0);
    for(let a=-1;a<=1;a++)add(new THREE.BoxGeometry(.035,.55,.02),paperMat,a*.2,.4,.35);
  }else if(type==="stool"){
    w=.72;h=.62;depth=.72;add(new THREE.CylinderGeometry(.34,.34,.12,10),woodMat,0,.56,0);
    for(let a=0;a<4;a++){const t=a*Math.PI/2;add(new THREE.BoxGeometry(.07,.52,.07),darkMat,Math.cos(t)*.23,.27,Math.sin(t)*.23)}
  }else if(type==="basket"){
    w=.72;h=.52;depth=.72;add(new THREE.CylinderGeometry(.32,.25,.46,10,1,true),woodMat,0,.24,0);
    add(new THREE.TorusGeometry(.29,.035,6,14),darkMat,0,.49,0);
    for(let a=0;a<6;a++){const t=a*Math.PI/3;add(new THREE.BoxGeometry(.025,.42,.025),darkMat,Math.cos(t)*.27,.24,Math.sin(t)*.27)}
  }else if(type==="guitar"){
    w=.72;h=1.05;depth=.3;add(new THREE.SphereGeometry(.32,12,9),woodMat,0,.3,0);
    add(new THREE.SphereGeometry(.23,12,9),woodMat,0,.57,0);
    add(new THREE.BoxGeometry(.12,.72,.1),darkMat,0,.88,0);
    add(new THREE.BoxGeometry(.17,.14,.13),paperMat,0,1.27,0);
  }else if(type==="flowerpot"){
    w=.62;h=.62;depth=.62;add(new THREE.CylinderGeometry(.2,.29,.52,10),paperMat,0,.26,0);
    add(new THREE.CylinderGeometry(.31,.31,.07,10),darkMat,0,.55,0);
    for(let a=0;a<3;a++){const leaf=add(new THREE.SphereGeometry(.13,8,6),woodMat,(a-1)*.16,.72+(a%2)*.08,0);leaf.scale.set(.7,1.5,.6)}
  }else if(type==="toycar"){
    w=.9;h=.42;depth=.58;add(new THREE.BoxGeometry(.88,.23,.52),paperMat,0,.2,0);
    add(new THREE.BoxGeometry(.42,.2,.42),woodMat,0,.4,0);
    for(let a of [-1,1])for(let b of [-1,1]){const wheel=add(new THREE.CylinderGeometry(.09,.09,.07,9),darkMat,a*.29,.1,b*.25);wheel.rotation.z=Math.PI/2}
  }else if(type==="foldedchair"){
    w=.78;h=.98;depth=.48;add(new THREE.BoxGeometry(.65,.08,.48),woodMat,0,.38,0);
    add(new THREE.BoxGeometry(.65,.58,.07),paperMat,0,.68,-.2);
    for(let a of [-1,1]){add(new THREE.BoxGeometry(.055,.92,.055),darkMat,a*.28,.47,0);add(new THREE.BoxGeometry(.055,.55,.055),darkMat,a*.28,.29,.28)}
  }else if(type==="fan"){
    w=.72;h=1.02;depth=.42;add(new THREE.BoxGeometry(.48,.08,.38),darkMat,0,.04,0);
    add(new THREE.CylinderGeometry(.045,.045,.58,8),woodMat,0,.36,0);
    add(new THREE.TorusGeometry(.31,.035,7,16),darkMat,0,.76,0);
    for(let a=0;a<5;a++){const t=a*Math.PI*2/5;add(new THREE.BoxGeometry(.1,.42,.045),paperMat,Math.cos(t)*.12,.76+Math.sin(t)*.12,0,t)}
  }else if(type==="telescope"){
    w=1.05;h=.95;depth=.65;add(new THREE.CylinderGeometry(.12,.16,.72,10),darkMat,0,.76,0,Math.PI/2);
    for(let a of [-1,1])add(new THREE.BoxGeometry(.06,.66,.06),woodMat,a*.28,.33,0);
    add(new THREE.BoxGeometry(.72,.06,.62),paperMat,0,.06,0);
  }else if(type==="rolledpaper"){
    w=1.05;h=.32;depth=.55;add(new THREE.CylinderGeometry(.16,.16,w,10),paperMat,0,.17,0,Math.PI/2);
    add(new THREE.TorusGeometry(.16,.025,5,12),darkMat,-.36,.17,0,Math.PI/2);
    add(new THREE.TorusGeometry(.16,.025,5,12),darkMat,.36,.17,0,Math.PI/2);
  }else{
    w=.95;h=.35;depth=.7;add(new THREE.BoxGeometry(w,h,depth),paperMat,0,h/2,0);
  }
  addSketchOutlines(group);addGraphiteHatching(group,variationSeed);obstacles.push({mesh:group,x,z,w:w*sx,h:h*sy,type,passed:false});
 }
 // 10,000+ procedural combinations: 36 silhouettes, seeded scale, rotation,
 // lane placement and paired arrangements. The shuffled pool avoids short repeats.
 const obstacleCatalog=["branch","log","rock","crate","barrier","stump","bucket","cone","pencil","books","rubble","chair","umbrella","ladder","wheel","suitcase","lamp","hoop","cans","newspaper","sign","backpack","helmet","skateboard","ball","bottle","bin","stool","basket","guitar","flowerpot","toycar","foldedchair","fan","telescope","rolledpaper"];
 // Offline adaptive AI director: no network, API key or gameplay latency.
 let patternIndex=0,randomState=0x13a5c79,shapeBag=[],recentShapes=[];
 const aiRandom=()=>{randomState^=randomState<<13;randomState^=randomState>>>17;randomState^=randomState<<5;return (randomState>>>0)/4294967296};
 function nextShape(){
  if(!shapeBag.length){shapeBag=obstacleCatalog.slice();for(let i=shapeBag.length-1;i>0;i--){const j=Math.floor(aiRandom()*(i+1));[shapeBag[i],shapeBag[j]]=[shapeBag[j],shapeBag[i]]}}
  let pick=shapeBag.pop();
  if(recentShapes.slice(-3).includes(pick)&&shapeBag.length){shapeBag.unshift(pick);pick=shapeBag.pop()}
  recentShapes.push(pick);if(recentShapes.length>6)recentShapes.shift();
  return pick;
 }
 const aiDirector={get level(){return Math.round(skill*100)},get density(){return clamp(.25+skill*.55,.25,.8)},recordPass(){skill=clamp(skill+.012,0,1)},recordHit(){skill=clamp(skill-.22,0,1)},nextGap(){const challenge=clamp(skill*.72+(speed-1)*.035,0,.92);return Math.max(1.05,4.5-challenge*2.3+aiRandom()*.8)/(.78+speed*.13)}};
 function spawn(){
  const variant=patternIndex++,x=24,lanes=[-1.65,0,1.65];
  const first=Math.floor(aiRandom()*3),baseType=nextShape();
  const shapeSeed=(variant*7919+Math.floor(aiRandom()*65535))>>>0;
  obstacleShape(x,lanes[first],baseType,shapeSeed);
  // Keep at least one lane open; the director raises density as the player improves.
  if(aiRandom()<aiDirector.density){
   const choices=[0,1,2].filter(i=>i!==first),second=choices[Math.floor(aiRandom()*choices.length)];
   obstacleShape(x,lanes[second],nextShape(),(shapeSeed*3+17)>>>0);
  }
  nextSpawn=aiDirector.nextGap();
 }
 function setText(id,s){document.getElementById(id).textContent=s}
 function disposeTree(root){
  const geometries=new Set(),materials=new Set();
  root.traverse(o=>{
   if(o.geometry)geometries.add(o.geometry);
   for(const m of (Array.isArray(o.material)?o.material:[o.material]))if(m)materials.add(m);
  });
  for(const g of geometries)g.dispose();
  for(const m of (root.userData.ownedMaterials||[]))if(m)materials.add(m);
  for(const m of materials)m.dispose();
  scene.remove(root);
 }
 function reset(){obstacles.splice(0).forEach(o=>disposeTree(o.mesh));score=0;elapsed=0;lastStep=0;nextSpawn=.8;jumpY=0;jumpV=0;grounded=true;skill=.3;streak=0;travelDistance=0;laneZ=0;targetLaneZ=0;runner.position.set(-2.25,0,0);runner.rotation.set(0,0,0);updateTrack();dead=false;paused=false;msg.innerHTML="";setText("pause","Ⅱ")}
 function jump(){if(dead||paused){if(dead||!started){reset();started=true}return}if(grounded){jumpV=8.6;grounded=false;runner.rotation.z=-.12;tone(260,.12,"triangle",.04,180)}}
 let started=false;const msg=document.getElementById("message");
 document.getElementById("jump").addEventListener("pointerdown",e=>{e.preventDefault();jump()});
 document.getElementById("pause").addEventListener("click",()=>{if(dead||!started){reset();started=true;return}paused=!paused;setText("pause",paused?"▶":"Ⅱ");msg.textContent=paused?"ПАУЗА":""});
 document.getElementById("speed").addEventListener("input",e=>{speed=+e.target.value;setText("speedVal",speed+" / 10")});
 function steer(dir){if(dead||paused||!started)return;targetLaneZ=clamp(targetLaneZ+dir*1.05,-1.85,1.85)}
 window.addEventListener("keydown",e=>{if(e.code==="ArrowLeft"||e.code==="KeyA"){e.preventDefault();steer(-1)}if(e.code==="ArrowRight"||e.code==="KeyD"){e.preventDefault();steer(1)}});
 let swipeX=null;canvas.addEventListener("pointerdown",e=>{swipeX=e.clientX});canvas.addEventListener("pointerup",e=>{if(swipeX===null)return;const dx=e.clientX-swipeX;if(Math.abs(dx)>24)steer(dx>0?1:-1);swipeX=null});
 msg.addEventListener("click",e=>{if(e.target&&e.target.id==="play"){reset();started=true}});
 document.getElementById("sound").addEventListener("click",e=>{soundEnabled=!soundEnabled;e.currentTarget.textContent=soundEnabled?"♪":"×";if(soundEnabled){audioReady();tone(520,.07,"sine",.025)}});
 document.querySelectorAll("[data-view]").forEach((b,i)=>b.addEventListener("click",()=>{view=i;document.querySelectorAll("[data-view]").forEach(x=>x.classList.toggle("active",x===b))}));
 window.addEventListener("keydown",e=>{if(e.code==="Space"||e.code==="ArrowUp"){e.preventDefault();jump()}if(e.code==="Escape"){paused=!paused;setText("pause",paused?"▶":"Ⅱ")}});
 document.addEventListener("visibilitychange",()=>{if(document.hidden&&started&&!dead){paused=true;setText("pause","▶");msg.textContent="ПАУЗА"}});
 window.addEventListener("pagehide",()=>{try{localStorage.setItem("rm3dBest",String(Math.max(best,Math.floor(score))))}catch(e){}});
 const clock=new THREE.Clock();let frameAccumulator=0;
 function frame(){
  requestAnimationFrame(frame);
  frameAccumulator+=clock.getDelta();
  if(frameAccumulator<1/30)return;
  const dt=Math.min(frameAccumulator,.05);
  frameAccumulator=0;
  if(!paused&&!dead&&started){
   elapsed+=dt;score+=dt*speed*2;const velocity=1.15+speed*1.08;
   travelDistance+=velocity*dt;updateTrack();
   laneZ+=(targetLaneZ-laneZ)*(1-Math.exp(-8*dt));runner.position.z=laneZ;
   if(mixer){mixer.timeScale=.35+speed*.19;mixer.update(dt)}
   else if(runner.userData.limbs&&runner.userData.limbs[0]?.leg?.parent){const p=elapsed*velocity*1.8;runner.userData.limbs.forEach((l,i)=>{l.leg.rotation.x=Math.sin(p+i*Math.PI)*.75;l.arm.rotation.x=-Math.sin(p+i*Math.PI)*.65;l.foot.rotation.x=l.leg.rotation.x*.25})}
   else if(runner.userData.model){const p=elapsed*velocity*3.2;runner.userData.model.position.y=runner.userData.modelBaseY+Math.abs(Math.sin(p))*.025;runner.userData.model.rotation.z=Math.sin(p)*.018}
   if(!grounded){jumpV-=21*dt;jumpY+=jumpV*dt;if(jumpY<=0){jumpY=0;jumpV=0;grounded=true;runner.rotation.z=0;tone(92,.07,"triangle",.022,-24)}}
   if(grounded&&elapsed-lastStep>Math.max(.22,.48/(.5+speed*.14))){tone(68,.045,"sine",.012,-12);lastStep=elapsed}
   runner.position.y=jumpY;runner.position.x=-2.25;

   nextSpawn-=dt;if(nextSpawn<=0)spawn();

   for(let i=obstacles.length-1;i>=0;i--){const o=obstacles[i];o.x-=velocity*dt;o.mesh.position.x=o.x;o.mesh.position.z=pathZ(o.x)+o.z;
    if(!o.passed&&o.x< -2.7){o.passed=true;streak++;aiDirector.recordPass()}
    if(Math.abs(o.x+2.25)<(o.w*.5+.28)&&jumpY<o.h*.83&&Math.abs(o.z-laneZ)<.48){dead=true;impactSound();aiDirector.recordHit();best=Math.max(best,Math.floor(score));try{localStorage.setItem("rm3dBest",best)}catch(e){}msg.innerHTML="СТОЛКНОВЕНИЕ<br>СЧЁТ: "+Math.floor(score)+" · РЕКОРД: "+best+"<br><button id='retry'>ЕЩЁ РАЗ</button>";document.getElementById("retry").onclick=()=>{reset();started=true};break}
    if(o.x< -18){disposeTree(o.mesh);obstacles.splice(i,1)}
   }
   setText("score","СЧЁТ "+String(Math.floor(score)).padStart(6,"0")+" · РЕКОРД "+String(best).padStart(6,"0"));
  }
  // Third-person chase view: the runner advances along +X and the camera follows from behind.
  const target=view===0?new THREE.Vector3(2.8,1.05,pathZ(2.8)+laneZ*.72):view===1?new THREE.Vector3(2.4,1.15,pathZ(2.4)+laneZ*.72+4.8):new THREE.Vector3(-1.8,1.2,pathZ(-1.8)+laneZ*.72);
  const pos=view===0?new THREE.Vector3(-8.5,3.05,pathZ(-8.5)+laneZ+0.15):view===1?new THREE.Vector3(-7.2,3.55,pathZ(-7.2)+laneZ+6.2):new THREE.Vector3(8.5,3.1,pathZ(8.5)+laneZ);
  camera.position.lerp(pos,1-Math.pow(.001,dt));camera.fov=THREE.MathUtils.lerp(camera.fov,54+(speed-1)*.32,1-Math.pow(.01,dt));camera.lookAt(target);
  const w=canvas.clientWidth,h=canvas.clientHeight;if(canvas.width!==Math.floor(w*renderer.getPixelRatio())||canvas.height!==Math.floor(h*renderer.getPixelRatio()))renderer.setSize(w,h,false);camera.aspect=w/Math.max(h,1);camera.updateProjectionMatrix();renderer.render(scene,camera);
 }
 msg.innerHTML="БЕГУЩИЙ ЧЕЛОВЕК<br><small>АДАПТИВНЫЙ ИИ-ДИРЕКТОР · БЕСКОНЕЧНЫЙ БЕГ</small><br><button id='play'>НАЧАТЬ</button>";
 frame();
}
