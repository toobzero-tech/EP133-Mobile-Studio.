import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export function start(){
 const canvas=document.querySelector("#stage"),scene=new THREE.Scene();
 scene.background=new THREE.Color(0xfaf9f6);
 const pathZ=x=>1.35*Math.sin(x*.052)+.48*Math.sin(x*.117+.6);
 const camera=new THREE.PerspectiveCamera(54,1,.1,140);camera.position.set(-10,3.35,0);camera.lookAt(5.5,1.05,0);
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,1.35));renderer.shadowMap.enabled=false;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
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
  ctx.fillStyle="#f4f1eb";ctx.fillRect(0,0,256,256);
  for(let pass=0;pass<3;pass++){ctx.strokeStyle=pass===0?"rgba(35,33,30,.13)":"rgba(35,33,30,.075)";ctx.lineWidth=pass===0?.7:.45;
   for(let i=0;i<170;i++){const x=Math.random()*256,y=Math.random()*256,len=5+Math.random()*30;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+len,y-len*(pass===1?.18:.72));ctx.stroke()}}
  for(let i=0;i<900;i++){const x=Math.random()*256,y=Math.random()*256;ctx.fillStyle="rgba(30,28,26,"+(Math.random()*.11)+")";ctx.fillRect(x,y,.7,.7)}
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(2,2);t.colorSpace=THREE.SRGBColorSpace;return t;
 }
 const graphiteTexture=makeGraphiteTexture();
 const floorMat=mat(0xbcb4a6);floorMat.map=paperTexture;floorMat.needsUpdate=true;
 const lineMat=mat(0x777064),wood=mat(0xc99a55),graphite=mat(0x302d29),eraser=mat(0xb97875),paper=mat(0xe5ddce);
 const floor=new THREE.Mesh(new THREE.PlaneGeometry(200,200),floorMat);floor.rotation.x=-Math.PI/2;floor.position.y=-.08;scene.add(floor);
 const trackPositions=[],trackIndices=[],leftEdge=[],rightEdge=[];
 const trackSegments=180,trackStart=-35,trackEnd=45,trackWidth=5.2;
 for(let i=0;i<=trackSegments;i++){
  const x=trackStart+(trackEnd-trackStart)*i/trackSegments,center=pathZ(x);
  trackPositions.push(x,-.012,center-trackWidth/2,x,-.012,center+trackWidth/2);
  leftEdge.push(new THREE.Vector3(x,.006,center-trackWidth/2));rightEdge.push(new THREE.Vector3(x,.006,center+trackWidth/2));
  if(i<trackSegments){const n=i*2;trackIndices.push(n,n+1,n+2,n+1,n+3,n+2)}
 }
 const trackGeometry=new THREE.BufferGeometry();trackGeometry.setAttribute("position",new THREE.Float32BufferAttribute(trackPositions,3));trackGeometry.setIndex(trackIndices);trackGeometry.computeVertexNormals();
 const trackMaterial=mat(0xe4e0d8);trackMaterial.side=THREE.DoubleSide;scene.add(new THREE.Mesh(trackGeometry,trackMaterial));
 const trackInk=new THREE.LineBasicMaterial({color:0x77716a,transparent:true,opacity:.42});
 scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(leftEdge),trackInk));scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(rightEdge),trackInk));
 const runner=new THREE.Group();runner.position.set(-2.25,0,0);scene.add(runner);
 let mixer=null,runAction=null,modelReady=false;
 function fallbackRunner(){
  const skin=mat(0xc69d7d),shirt=mat(0x555b5c),pants=mat(0x34383a),shoe=mat(0x252525);
  const sphere=(r,m,x,y,z)=>{const o=new THREE.Mesh(new THREE.SphereGeometry(r,20,16),m);o.position.set(x,y,z);runner.add(o);return o};
  const torso=new THREE.Mesh(new THREE.CapsuleGeometry(.29,.62,6,12),shirt);torso.position.y=1.12;torsrunner.add(torso);
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
 fallbackRunner();addSketchOutlines(runner);
 const loader=new GLTFLoader();
 loader.load("./runner.glb",g=>{
  const oldGeometry=new Set(),oldMaterials=new Set();
  runner.traverse(o=>{if(o.isMesh){if(o.geometry)oldGeometry.add(o.geometry);for(const m of (Array.isArray(o.material)?o.material:[o.material]))if(m)oldMaterials.add(m)}});
  while(runner.children.length)runner.remove(runner.children[0]);
  oldGeometry.forEach(v=>v.dispose());oldMaterials.forEach(v=>v.dispose());
  const model=g.scene;const box=new THREE.Box3().setFromObject(model),size=box.getSize(new THREE.Vector3());const scale=1.78/Math.max(size.y,.01);model.scale.setScalar(scale);const b2=new THREE.Box3().setFromObject(model);model.position.y-=b2.min.y;model.traverse(o=>{if(o.isMesh){
   const source=Array.isArray(o.material)?o.material:[o.material];
   const pencilMats=source.map(m=>new THREE.MeshStandardMaterial({color:grayColor(m?.color??0x777777),map:graphiteTexture,roughness:1,metalness:0}));
   o.material=Array.isArray(o.material)?pencilMats:pencilMats[0];
  }});runner.add(model);addSketchOutlines(model);
  if(g.animations.length){mixer=new THREE.AnimationMixer(model);const clip=g.animations.find(a=>/run|jog|sprint/i.test(a.name))||g.animations[0];runAction=mixer.clipAction(clip);runAction.play()}
  modelReady=true;
 },undefined,()=>{});
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
  }else{
    w=.95;h=.35;depth=.7;add(new THREE.BoxGeometry(w,h,depth),paperMat,0,h/2,0);
  }
  addSketchOutlines(group);obstacles.push({mesh:group,x,z,w:w*sx,h:h*sy,type,passed:false});
 }
 // 1,000+ procedural combinations: shape, scale, lane offset, stacked variants,
 // rotations and paired/triple arrangements. The pool cycles in shuffled order.
 const obstacleCatalog=["branch","log","rock","crate","barrier","stump","bucket","cone","pencil","books","rubble"];
 let patternIndex=0;
 function spawn(){
  const variant=patternIndex++;
  const baseIndex=(variant*7+Math.floor(variant/11))%obstacleCatalog.length;
  const baseType=obstacleCatalog[baseIndex];
  const x=24,lanes=[-1.65,0,1.65];
  const first=(variant*5+Math.floor(variant/7))%3,combo=variant%11;
  obstacleShape(x,lanes[first],baseType,variant);
  // Leave at least one clear lane in every obstacle row.
  if(combo!==0){
   const choices=[0,1,2].filter(i=>i!==first);
   const second=choices[(Math.floor(variant/3)+Math.floor(variant/13))%2];
   const secondType=combo===3?"log":combo===4?"branch":combo===6?"cone":obstacleCatalog[(variant*13+Math.floor(variant/5)+3)%obstacleCatalog.length];
   obstacleShape(x,lanes[second],secondType,variant*3+17);
  }
  nextSpawn=Math.max(.9,(4.2-skill*1.35)+(Math.random()*.7))/((.72+speed*.14));
 }
 function setText(id,s){document.getElementById(id).textContent=s}
 function disposeTree(root){
  root.traverse(o=>{
   if(o.geometry)o.geometry.dispose();
   if(o.isLineSegments&&o.material&&o.material.dispose)o.material.dispose();
  });
  for(const m of (root.userData.ownedMaterials||[]))m.dispose();
  scene.remove(root);
 }
 function reset(){obstacles.splice(0).forEach(o=>disposeTree(o.mesh));score=0;elapsed=0;lastStep=0;nextSpawn=.8;jumpY=0;jumpV=0;grounded=true;skill=.3;streak=0;dead=false;paused=false;msg.innerHTML="";setText("pause","Ⅱ")}
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
 const clock=new THREE.Clock();let frameAccumulator=0;
 function frame(){
  requestAnimationFrame(frame);
  frameAccumulator+=clock.getDelta();
  if(frameAccumulator<1/30)return;
  const dt=Math.min(frameAccumulator,.05);
  frameAccumulator=0;
  if(!paused&&!dead&&started){
   elapsed+=dt;score+=dt*speed*2;const velocity=1.15+speed*1.08;
   laneZ+=(targetLaneZ-laneZ)*(1-Math.exp(-8*dt));runner.position.z=pathZ(-2.25)+laneZ;
   if(mixer){mixer.timeScale=.35+speed*.19;mixer.update(dt)}else if(runner.userData.limbs){const p=elapsed*velocity*1.8;runner.userData.limbs.forEach((l,i)=>{l.leg.rotation.x=Math.sin(p+i*Math.PI)*.75;l.arm.rotation.x=-Math.sin(p+i*Math.PI)*.65;l.foot.rotation.x=l.leg.rotation.x*.25})}
   if(!grounded){jumpV-=21*dt;jumpY+=jumpV*dt;if(jumpY<=0){jumpY=0;jumpV=0;grounded=true;tone(92,.07,"triangle",.022,-24)}}
   if(grounded&&elapsed-lastStep>Math.max(.22,.48/(.5+speed*.14))){tone(68,.045,"sine",.012,-12);lastStep=elapsed}
   runner.position.y=jumpY;runner.position.x=-2.25;

   nextSpawn-=dt;if(nextSpawn<=0)spawn();
   for(let i=obstacles.length-1;i>=0;i--){const o=obstacles[i];o.x-=velocity*dt;o.mesh.position.x=o.x;o.mesh.position.z=pathZ(o.x)+o.z;
    if(!o.passed&&o.x< -2.7){o.passed=true;streak++;skill=clamp(skill+.025,0,1)}
    if(Math.abs(o.x+2.25)<(o.w*.5+.28)&&jumpY<o.h*.83&&Math.abs(o.z-laneZ)<.48){dead=true;impactSound();skill=clamp(skill-.2,0,1);best=Math.max(best,Math.floor(score));try{localStorage.setItem("rm3dBest",best)}catch(e){}msg.innerHTML="СТОЛКНОВЕНИЕ<br>СЧЁТ: "+Math.floor(score)+" · РЕКОРД: "+best+"<br><button id='retry'>ЕЩЁ РАЗ</button>";document.getElementById("retry").onclick=()=>{reset();started=true};break}
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
 msg.innerHTML="БЕГУЩИЙ ЧЕЛОВЕК<br><small>3D · РЕАЛИСТИЧНЫЙ БЕГ</small><br><button id='play'>НАЧАТЬ</button>";
 frame();
}
