import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export function start(){
 const canvas=document.querySelector("#stage"),scene=new THREE.Scene();
 scene.background=new THREE.Color(0xeee9df);scene.fog=new THREE.Fog(0xeee9df,22,88);
 const camera=new THREE.PerspectiveCamera(54,1,.1,140);camera.position.set(-10,3.35,0);camera.lookAt(5.5,1.05,0);
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,1.8));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
 scene.add(new THREE.HemisphereLight(0xf4eee2,0x756b5b,2.0));
 const sun=new THREE.DirectionalLight(0xffedcf,3.2);sun.position.set(-5,10,7);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-18;sun.shadow.camera.right=18;sun.shadow.camera.top=18;sun.shadow.camera.bottom=-18;scene.add(sun);
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
  ctx.fillStyle="#e9e4d9";ctx.fillRect(0,0,512,512);
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
 const floor=new THREE.Mesh(new THREE.PlaneGeometry(200,200),floorMat);floor.rotation.x=-Math.PI/2;floor.position.y=-.08;floor.receiveShadow=true;scene.add(floor);
 const lane=new THREE.Mesh(new THREE.BoxGeometry(200,.08,5.2),mat(0xc9c1b3));lane.position.set(0,-.02,0);lane.receiveShadow=true;scene.add(lane);
 for(let z=-2.4;z<=2.4;z+=.8){const l=new THREE.Mesh(new THREE.BoxGeometry(200,.012,.012),lineMat);l.position.set(0,.03,z);scene.add(l)}
 const runner=new THREE.Group();runner.position.set(-2.25,0,0);scene.add(runner);
 const runnerShadow=new THREE.Mesh(new THREE.CircleGeometry(.48,32),new THREE.MeshBasicMaterial({color:0x292622,transparent:true,opacity:.2,depthWrite:false}));
 runnerShadow.rotation.x=-Math.PI/2;runnerShadow.position.set(-2.25,-.055,0);scene.add(runnerShadow);
 let mixer=null,runAction=null,modelReady=false;
 function fallbackRunner(){
  const skin=mat(0xc69d7d),shirt=mat(0x555b5c),pants=mat(0x34383a),shoe=mat(0x252525);
  const sphere=(r,m,x,y,z)=>{const o=new THREE.Mesh(new THREE.SphereGeometry(r,20,16),m);o.position.set(x,y,z);o.castShadow=true;runner.add(o);return o};
  const torso=new THREE.Mesh(new THREE.CapsuleGeometry(.29,.62,6,12),shirt);torso.position.y=1.12;torso.castShadow=true;runner.add(torso);
  sphere(.19,skin,0,1.78,0);
  const limbs=[];
  for(let side of [-1,1]){
   let leg=new THREE.Mesh(new THREE.CapsuleGeometry(.105,.53,5,10),pants);leg.position.set(side*.14,.48,0);leg.castShadow=true;runner.add(leg);
   let arm=new THREE.Mesh(new THREE.CapsuleGeometry(.075,.5,5,10),skin);arm.position.set(side*.34,1.18,0);arm.castShadow=true;runner.add(arm);
   let foot=new THREE.Mesh(new THREE.BoxGeometry(.2,.12,.36),shoe);foot.position.set(side*.14,.08,.09);foot.castShadow=true;runner.add(foot);
   limbs.push({leg,arm,foot,side});
  }
  runner.userData.limbs=limbs;
 }
 fallbackRunner();addSketchOutlines(runner);
 const loader=new GLTFLoader();
 loader.load("./runner.glb",g=>{
  while(runner.children.length)runner.remove(runner.children[0]);
  const model=g.scene;const box=new THREE.Box3().setFromObject(model),size=box.getSize(new THREE.Vector3());const scale=1.78/Math.max(size.y,.01);model.scale.setScalar(scale);const b2=new THREE.Box3().setFromObject(model);model.position.y-=b2.min.y;model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;
   const source=Array.isArray(o.material)?o.material:[o.material];
   const pencilMats=source.map(m=>new THREE.MeshStandardMaterial({color:grayColor(m?.color??0x777777),map:graphiteTexture,roughness:1,metalness:0}));
   o.material=Array.isArray(o.material)?pencilMats:pencilMats[0];
  }});runner.add(model);addSketchOutlines(model);
  if(g.animations.length){mixer=new THREE.AnimationMixer(model);const clip=g.animations.find(a=>/run|jog|sprint/i.test(a.name))||g.animations[0];runAction=mixer.clipAction(clip);runAction.play()}
  modelReady=true;
 },undefined,()=>{});
 const obstacles=[];let nextSpawn=1.2,elapsed=0,score=0,best=+(localStorage.getItem("rm3dBest")||0),speed=5,paused=true,dead=false,jumpY=0,jumpV=0,grounded=true,skill=.3,streak=0,view=0;
 let audio=null,soundEnabled=true,lastStep=0;
 function audioReady(){if(!soundEnabled)return null;try{if(!audio){const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return null;audio=new AC()}if(audio.state==="suspended")audio.resume();return audio}catch(e){return null}}
 function tone(freq,duration=.09,type="sine",volume=.045,slide=0){const ctx=audioReady();if(!ctx)return;const osc=ctx.createOscillator(),gain=ctx.createGain();osc.type=type;osc.frequency.setValueAtTime(freq,ctx.currentTime);if(slide)osc.frequency.exponentialRampToValueAtTime(Math.max(30,freq+slide),ctx.currentTime+duration);gain.gain.setValueAtTime(.0001,ctx.currentTime);gain.gain.exponentialRampToValueAtTime(volume,ctx.currentTime+.012);gain.gain.exponentialRampToValueAtTime(.0001,ctx.currentTime+duration);osc.connect(gain);gain.connect(ctx.destination);osc.start();osc.stop(ctx.currentTime+duration+.02)}
 function impactSound(){tone(115,.16,"triangle",.065,-65);tone(62,.22,"sine",.045,-28)}

 function pencil(x,z,h=1.0){
  const group=new THREE.Group();group.position.set(x,0,z);
  const body=new THREE.Mesh(new THREE.CylinderGeometry(.075,.075,h-.18,12),wood);body.position.y=(h-.18)/2+.09;body.castShadow=true;group.add(body);
  const tip=new THREE.Mesh(new THREE.ConeGeometry(.075,.18,12),wood);tip.position.y=h-.09;tip.castShadow=true;group.add(tip);
  const lead=new THREE.Mesh(new THREE.ConeGeometry(.025,.055,8),graphite);lead.position.y=h+.025;group.add(lead);
  const band=new THREE.Mesh(new THREE.CylinderGeometry(.078,.078,.07,12),eraser);band.position.y=.07;group.add(band);
  const rings=new THREE.Mesh(new THREE.CylinderGeometry(.079,.079,.018,12),mat(0xb9a88f,.45,.4));rings.position.y=.115;group.add(rings);
  scene.add(group);addSketchOutlines(group);obstacles.push({mesh:group,x,z,w:.42,h,type:"pencil",passed:false});
 }
 function boxObstacle(x,z,w,h,depth,color,type){
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,depth),mat(color));mesh.position.set(x,h/2,z);mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);addSketchOutlines(mesh);obstacles.push({mesh,x,z,w,h,type,passed:false});
 }
 function spawn(){
  const pool=skill<.25?["pencil","eraser","paper"]:skill<.55?["pencil","pencil","eraser","ruler","book"]:["pencil","eraser","ruler","book","stack"];
  const type=pool[Math.floor(Math.random()*pool.length)],x=24,z=(Math.random()-.5)*1.2;
  if(type==="pencil")pencil(x,z,.7+Math.random()*.55);
  else if(type==="eraser")boxObstacle(x,z,.8,.55,.6,0xb97875,type);
  else if(type==="ruler")boxObstacle(x,z,1.8,.22,.25,0xd2b981,type);
  else if(type==="book")boxObstacle(x,z,.85,.72,.65,0x746b61,type);
  else if(type==="stack"){pencil(x,z,.85);pencil(x,z+.35,.7)}
  else boxObstacle(x,z,1.1,.32,.04,0xe1d9c9,"paper");
  nextSpawn=Math.max(1.0,(3.9-skill*1.5)+(Math.random()*.8))/((.75+speed*.13));
 }
 function setText(id,s){document.getElementById(id).textContent=s}
 function reset(){obstacles.splice(0).forEach(o=>scene.remove(o.mesh));score=0;elapsed=0;nextSpawn=.8;jumpY=0;jumpV=0;grounded=true;skill=.3;streak=0;dead=false;paused=false;msg.innerHTML="";setText("pause","Ⅱ")}
 function jump(){if(dead||paused){if(dead||!started){reset();started=true}return}if(grounded){jumpV=8.6;grounded=false;runner.rotation.z=-.12;tone(260,.12,"triangle",.04,180)}}
 let started=false;const msg=document.getElementById("message");
 document.getElementById("jump").addEventListener("pointerdown",e=>{e.preventDefault();jump()});
 document.getElementById("pause").addEventListener("click",()=>{if(dead||!started){reset();started=true;return}paused=!paused;setText("pause",paused?"▶":"Ⅱ");msg.textContent=paused?"ПАУЗА":""});
 document.getElementById("speed").addEventListener("input",e=>{speed=+e.target.value;setText("speedVal",speed+" / 10")});
 msg.addEventListener("click",e=>{if(e.target&&e.target.id==="play"){reset();started=true}});
 document.getElementById("sound").addEventListener("click",e=>{soundEnabled=!soundEnabled;e.currentTarget.textContent=soundEnabled?"♪":"×";if(soundEnabled){audioReady();tone(520,.07,"sine",.025)}});
 document.querySelectorAll("[data-view]").forEach((b,i)=>b.addEventListener("click",()=>{view=i;document.querySelectorAll("[data-view]").forEach(x=>x.classList.toggle("active",x===b))}));
 window.addEventListener("keydown",e=>{if(e.code==="Space"||e.code==="ArrowUp"){e.preventDefault();jump()}if(e.code==="Escape"){paused=!paused;setText("pause",paused?"▶":"Ⅱ")}});
 const clock=new THREE.Clock();
 function frame(){
  requestAnimationFrame(frame);const dt=Math.min(clock.getDelta(),.04);
  if(!paused&&!dead&&started){
   elapsed+=dt;score+=dt*speed*2;const velocity=5.5+speed*.78;
   if(mixer)mixer.update(dt);else if(runner.userData.limbs){const p=elapsed*velocity*1.8;runner.userData.limbs.forEach((l,i)=>{l.leg.rotation.x=Math.sin(p+i*Math.PI)*.75;l.arm.rotation.x=-Math.sin(p+i*Math.PI)*.65;l.foot.rotation.x=l.leg.rotation.x*.25})}
   if(!grounded){jumpV-=21*dt;jumpY+=jumpV*dt;if(jumpY<=0){jumpY=0;jumpV=0;grounded=true}}
   runner.position.y=jumpY;runner.position.x=-2.25;
   runnerShadow.position.x=-2.25;runnerShadow.scale.setScalar(1/(1+jumpY*.35));runnerShadow.material.opacity=.2/(1+jumpY*.7);
   nextSpawn-=dt;if(nextSpawn<=0)spawn();
   for(let i=obstacles.length-1;i>=0;i--){const o=obstacles[i];o.x-=velocity*dt;o.mesh.position.x=o.x;
    if(!o.passed&&o.x< -2.7){o.passed=true;streak++;skill=clamp(skill+.025,0,1)}
    if(Math.abs(o.x+2.25)<(o.w*.5+.28)&&jumpY<o.h*.83&&Math.abs(o.z)<.72){dead=true;impactSound();skill=clamp(skill-.2,0,1);best=Math.max(best,Math.floor(score));localStorage.setItem("rm3dBest",best);msg.innerHTML="СТОЛКНОВЕНИЕ<br>СЧЁТ: "+Math.floor(score)+" · РЕКОРД: "+best+"<br><button id='retry'>ЕЩЁ РАЗ</button>";document.getElementById("retry").onclick=()=>{reset();started=true};break}
    if(o.x< -18){scene.remove(o.mesh);obstacles.splice(i,1)}
   }
   setText("score","СЧЁТ "+String(Math.floor(score)).padStart(6,"0")+" · РЕКОРД "+String(best).padStart(6,"0"));
  }
  // Third-person chase view: the runner advances along +X and the camera follows from behind.
  const target=view===0?new THREE.Vector3(5.8,1.05,0):view===1?new THREE.Vector3(3.8,1.15,4.8):new THREE.Vector3(-1.8,1.2,0);
  const pos=view===0?new THREE.Vector3(-10,3.35,0):view===1?new THREE.Vector3(-7.8,3.8,6.2):new THREE.Vector3(8.5,3.1,0);
  camera.position.lerp(pos,1-Math.pow(.001,dt));camera.fov=THREE.MathUtils.lerp(camera.fov,54+(speed-1)*.32,1-Math.pow(.01,dt));camera.lookAt(target);
  const w=canvas.clientWidth,h=canvas.clientHeight;if(canvas.width!==Math.floor(w*renderer.getPixelRatio())||canvas.height!==Math.floor(h*renderer.getPixelRatio()))renderer.setSize(w,h,false);camera.aspect=w/Math.max(h,1);camera.updateProjectionMatrix();renderer.render(scene,camera);
 }
 msg.innerHTML="БЕГУЩИЙ ЧЕЛОВЕК<br><small>3D · РЕАЛИСТИЧНЫЙ БЕГ</small><br><button id='play'>НАЧАТЬ</button>";
 frame();
}
