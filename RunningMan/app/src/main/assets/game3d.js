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
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false,powerPreference:"high-performance"});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.shadowMap.enabled=false;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
 scene.add(new THREE.HemisphereLight(0xffffff,0xaaa49a,1.85));
 const sun=new THREE.DirectionalLight(0xffffff,1.25);sun.position.set(-5,10,7);scene.add(sun);
 const fillLight=new THREE.DirectionalLight(0xffffff,.32);fillLight.position.set(4,3,-6);scene.add(fillLight);
 const grayColor=color=>{const c=new THREE.Color(color);const y=.299*c.r+.587*c.g+.114*c.b;return new THREE.Color().setRGB(y,y,y)};
 // Four-step grayscale ramp: clear illustrated light/shadow planes instead of plastic PBR shading.
 const toonRampData=new Uint8Array([38,38,38,255,92,92,92,255,166,166,166,255,232,232,232,255]);
 const toonRamp=new THREE.DataTexture(toonRampData,4,1,THREE.RGBAFormat);
 toonRamp.magFilter=THREE.NearestFilter;toonRamp.minFilter=THREE.NearestFilter;toonRamp.generateMipmaps=false;toonRamp.needsUpdate=true;
 const mat=(color,roughness=.94,metalness=0)=>new THREE.MeshToonMaterial({color:grayColor(color),map:graphiteTexture,gradientMap:toonRamp});
 function addSketchOutlines(root){
  root.traverse(o=>{if(!o.isMesh||o.userData.sketchOutline)return;o.userData.sketchOutline=true;
   // A slightly finer crease threshold preserves clothing folds and limb
   // separation without outlining every polygon of the low-poly rig.
   const edges=new THREE.EdgesGeometry(o.geometry,31);
   const ink=new THREE.LineBasicMaterial({color:0x37332e,transparent:true,opacity:.235,depthWrite:false});
   const lines=new THREE.LineSegments(edges,ink);lines.renderOrder=2;o.add(lines);
  });
 }
 function makePaperTexture(){
  const c=document.createElement("canvas");c.width=c.height=1024;const ctx=c.getContext("2d");
  ctx.fillStyle="#faf9f6";ctx.fillRect(0,0,1024,1024);
  for(let i=0;i<58;i++){const x=Math.random()*1024,y=Math.random()*1024;const g=ctx.createLinearGradient(x-35,y-20,x+45,y+30);g.addColorStop(0,"rgba(90,85,78,.015)");g.addColorStop(.5,"rgba(255,255,255,.28)");g.addColorStop(1,"rgba(80,74,68,.045)");ctx.strokeStyle=g;ctx.lineWidth=1+Math.random()*3;ctx.beginPath();ctx.moveTo(x-35,y-20);ctx.quadraticCurveTo(x+5,y+35,x+45,y+30);ctx.stroke()}
  for(let i=0;i<26000;i++){const x=Math.random()*1024,y=Math.random()*1024,a=.018+Math.random()*.055;ctx.fillStyle="rgba(55,49,42,"+a+")";ctx.fillRect(x,y,Math.random()*1.5+.3,.5)}
  ctx.strokeStyle="rgba(65,59,51,.10)";ctx.lineWidth=.6;
  for(let i=0;i<180;i++){const x=Math.random()*1024,y=Math.random()*1024;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+5+Math.random()*24,y-2+Math.random()*4);ctx.stroke()}
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(14,14);t.colorSpace=THREE.SRGBColorSpace;return t;
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
  const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(2.5,2.5);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());return t;
 }
 const graphiteTexture=makeGraphiteTexture();
 const lineMat=mat(0x777064),wood=mat(0xc99a55),graphite=mat(0x302d29),eraser=mat(0xb97875),paper=mat(0xe5ddce);
 // The paper sheet is the complete backdrop. No floor, road, borders or scenery.
 paperTexture.wrapS=paperTexture.wrapT=THREE.ClampToEdgeWrapping;
 paperTexture.repeat.set(1,1);
 scene.background=paperTexture;
 // Visible track is drawn as broken graphite strokes directly on the paper.
 // It gives the runner depth without adding scenery, a floor mesh or heavy effects.
 const trackPositions=new Float32Array(2*2*92*3);
 const trackGeometry=new THREE.BufferGeometry();
 trackGeometry.setAttribute("position",new THREE.BufferAttribute(trackPositions,3));
 const trackInk=new THREE.LineBasicMaterial({color:0x77716a,transparent:true,opacity:.24,depthWrite:false,toneMapped:false});
 const trackLines=new THREE.LineSegments(trackGeometry,trackInk);
 trackLines.frustumCulled=false;trackLines.renderOrder=1;scene.add(trackLines);
 const trackTicks=[];
 for(let i=0;i<18;i++)trackTicks.push({x:-10+i*2.8,j:(i%3)*.025});
 function updateTrack(){
  let n=0;
  // Two irregular, lightly broken edges create a hand-drawn perspective path.
  for(let side of [-1,1]){
   for(let i=0;i<46;i++){
    const x=-17+i*1.28, x2=x+.58+(i%3)*.07;
    const wobble=Math.sin(i*1.71+side)*.045;
    const z=pathZ(x)+side*(2.48+wobble);
    const z2=pathZ(x2)+side*(2.48+Math.sin(i*1.31+side)*.045);
    trackPositions[n++]=x;trackPositions[n++]=.009;trackPositions[n++]=z;
    trackPositions[n++]=x2;trackPositions[n++]=.009;trackPositions[n++]=z2;
   }
  }
  trackGeometry.attributes.position.needsUpdate=true;
  trackGeometry.setDrawRange(0,n/3);
 }

 const runner=new THREE.Group();runner.position.set(-2.25,0,0);scene.add(runner);
 let mixer=null,runAction=null,modelReady=false;
 function fallbackRunner(){
  const skin=mat(0xb99b82),shirt=mat(0x55595a),pants=mat(0x343638),shoe=mat(0x252525),soleMat=mat(0x77736d),detail=mat(0x242424);
  const mesh=(geo,material,parent,x=0,y=0,z=0)=>{const o=new THREE.Mesh(geo,material);o.position.set(x,y,z);parent.add(o);return o};
  const sphere=(r,material,parent,x,y,z,sx=1,sy=1,sz=1)=>{const o=mesh(new THREE.SphereGeometry(r,18,14),material,parent,x,y,z);o.scale.set(sx,sy,sz);return o};
  // Rib cage and pelvis use overlapping tapered forms for a more human silhouette.
  const torso=new THREE.Group();torso.position.set(0,1.12,0);runner.add(torso);
  const chest=mesh(new THREE.CapsuleGeometry(.255,.38,7,16),shirt,torso,0,.12,0);chest.scale.set(1.02,1.12,.82);
  const pelvis=mesh(new THREE.SphereGeometry(.235,16,12),pants,torso,0,-.31,0);pelvis.scale.set(1.05,.72,.82);
  const collar=mesh(new THREE.CylinderGeometry(.105,.13,.075,12),detail,torso,0,.39,0);
  const neck=mesh(new THREE.CylinderGeometry(.078,.095,.17,12),skin,runner,0,1.57,0);
  const headGroup=new THREE.Group();headGroup.position.set(0,1.77,0);runner.add(headGroup);
  const head=sphere(.19,skin,headGroup,0,0,0,1,1.12,.91);
  // Ear, jaw, nose and hairline details keep the profile readable from the rear camera.
  sphere(.045,skin,headGroup,-.015,-.025,.177,.8,1,.65);
  const hair=mesh(new THREE.SphereGeometry(.194,18,12,0,Math.PI*2,0,Math.PI*.62),detail,headGroup,-.012,.055,0);hair.scale.set(1.02,1.08,.96);
  const nose=mesh(new THREE.ConeGeometry(.038,.09,8),skin,headGroup,.174,-.015,0);nose.rotation.z=-Math.PI/2;
  // Back-of-head hair contour and a small graphite neck seam.
  const hairline=mesh(new THREE.TorusGeometry(.155,.012,5,18,Math.PI),detail,headGroup,0,-.055,0);hairline.rotation.x=Math.PI/2;
  const limbs=[];
  for(const side of [-1,1]){
   const leg=new THREE.Group();leg.position.set(side*.145,.83,0);runner.add(leg);
   mesh(new THREE.CapsuleGeometry(.112,.36,6,12),pants,leg,0,-.205,0);
   const knee=sphere(.108,pants,leg,0,-.405,0,1,.92,.9);
   const shin=mesh(new THREE.CapsuleGeometry(.083,.34,6,12),pants,leg,0,-.625,0);shin.rotation.z=side*.025;
   const ankle=sphere(.078,pants,leg,0,-.81,0);
   const foot=new THREE.Group();foot.position.set(0,-.83,.025);leg.add(foot);
   mesh(new THREE.BoxGeometry(.19,.115,.34),shoe,foot,0,-.015,.105);
   mesh(new THREE.BoxGeometry(.195,.028,.345),soleMat,foot,0,-.075,.105);
   // Toe cap and heel seam are fine, low-contrast pencil details.
   mesh(new THREE.BoxGeometry(.15,.035,.105),detail,foot,0,.018,.245);
   const arm=new THREE.Group();arm.position.set(side*.285,1.43,0);runner.add(arm);
   mesh(new THREE.CapsuleGeometry(.086,.29,6,12),shirt,arm,0,-.17,0);
   const elbow=sphere(.075,skin,arm,0,-.345,0);
   const forearm=mesh(new THREE.CapsuleGeometry(.066,.27,6,12),skin,arm,0,-.51,0);
   const hand=sphere(.073,skin,arm,0,-.685,.012,.86,1,.78);
   // Subtle shirt cuff and trouser seam, kept monochrome.
   mesh(new THREE.TorusGeometry(.067,.008,4,12),detail,arm,0,-.405,0);
   limbs.push({leg,arm,foot,hand,side,knee,elbow,forearm});
  }
  // Shoulder blades and two restrained folds add depth without visual clutter.
  for(const side of [-1,1]){
   const fold=mesh(new THREE.BoxGeometry(.012,.22,.012),detail,torso,side*.17,.05,-.205);fold.rotation.z=side*.32;
  }
  runner.userData.limbs=limbs;runner.userData.torso=torso;runner.userData.head=headGroup;
 }
 fallbackRunner();addSketchOutlines(runner);addGraphiteHatching(runner,0x13a5);runner.userData.ownedMaterials=[];
 // Soft pencil contact shadow: a small mark on the paper, never a floor or scenery.
 const shadowCanvas=document.createElement("canvas");shadowCanvas.width=128;shadowCanvas.height=128;
 const shadowCtx=shadowCanvas.getContext("2d");
 const shadowGradient=shadowCtx.createRadialGradient(64,64,5,64,64,60);
 shadowGradient.addColorStop(0,"rgba(42,39,35,.30)");
 shadowGradient.addColorStop(.48,"rgba(42,39,35,.16)");
 shadowGradient.addColorStop(1,"rgba(42,39,35,0)");
 shadowCtx.fillStyle=shadowGradient;shadowCtx.fillRect(0,0,128,128);
 const shadowTexture=new THREE.CanvasTexture(shadowCanvas);shadowTexture.colorSpace=THREE.SRGBColorSpace;
 const runnerShadow=new THREE.Mesh(new THREE.PlaneGeometry(1.15,.72),new THREE.MeshBasicMaterial({map:shadowTexture,transparent:true,opacity:.72,depthWrite:false,toneMapped:false}));
 runnerShadow.rotation.x=-Math.PI/2;runnerShadow.position.set(-2.25,.012,0);runnerShadow.renderOrder=1;scene.add(runnerShadow);
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
    // Keep the licensed model's own surface maps and grayscale material identity.
    // The former pass disposed these maps and then ignored grayColor(), flattening
    // skin, clothes and shoes into one repeated graphite swatch.
    const color=grayColor(m?.color??0x777777);
    const map=m?.map||graphiteTexture;
    const bumpMap=m?.bumpMap||graphiteTexture;
    const material=new THREE.MeshToonMaterial({
     color,map,gradientMap:toonRamp,
     bumpMap,bumpScale:m?.bumpMap?.bumpScale??.018,
     alphaMap:m?.alphaMap||null,
     transparent:!!m?.transparent,
     opacity:m?.opacity??1,
     side:m?.side??THREE.FrontSide,
     vertexColors:!!m?.vertexColors
    });
    // Convert the final sampled surface to luminance in the shader. This keeps
    // the licensed model's UV detail while preventing colored source maps from
    // leaking color into the strict graphite-and-paper art direction.
    material.onBeforeCompile=shader=>{
     shader.fragmentShader=shader.fragmentShader.replace(
      "#include <map_fragment>",
      "#include <map_fragment>\n diffuseColor.rgb=vec3(dot(diffuseColor.rgb,vec3(0.299,0.587,0.114)));"
     );
    };
    material.customProgramCacheKey=()=>"running-man-graphite-luminance-v1";
    if(m)m.dispose();
    return material;
   });
   o.material=Array.isArray(o.material)?pencilMats:pencilMats[0];
  }});
  // Cache recognizable skeletal joints for a small procedural jump pose.
  // The offsets are applied after the authored run clip, so the original
  // animation remains in charge of the gait while the airborne pose bends joints.
  const jumpBones=[];
  model.traverse(o=>{
   if(!o.isBone)return;
   const n=(o.name||"").toLowerCase().replace(/[. _-]/g,"");
   const side=/left|\bl\b|\bleft/.test(n)?-1:/right|\br\b|\bright/.test(n)?1:0;
   let joint="";
   if(/upleg|thigh|femur/.test(n))joint="thigh";
   else if(/leg|calf|shin|knee/.test(n)&&!/upleg/.test(n))joint="calf";
   else if(/upperarm|arm|shoulder/.test(n))joint="upperArm";
   else if(/forearm|lowerarm|elbow/.test(n))joint="forearm";
   else if(/foot|ankle|toe/.test(n))joint="foot";
   else if(/spine|chest/.test(n))joint="spine";
   if(joint)jumpBones.push({bone:o,joint,side,offsetX:0});
  });
  runner.add(model);addSketchOutlines(model);model.userData.ownedMaterials=[];addGraphiteHatching(model,0x13a5);
  runner.userData.model=model;runner.userData.jumpBones=jumpBones;runner.userData.modelBaseY=model.position.y;
  if(g.animations.length){
   mixer=new THREE.AnimationMixer(model);
   // Prefer an actual locomotion cycle over an arbitrary first clip (often idle
   // or a preview pose in downloaded character assets).
   const ranked=g.animations.map(clip=>{
    const name=clip.name||"";
    const tracks=clip.tracks||[];
    const locomotion=/run|running|jog|sprint|locomotion/i.test(name);
    const idle=/idle|stand|rest|breath/i.test(name);
    const hasRootMotion=tracks.some(t=>/\.position$/.test(t.name));
    const duration=Number.isFinite(clip.duration)?clip.duration:0;
    const score=(locomotion?100:0)+(idle?-80:0)+Math.min(tracks.length,40)*.35+
     (duration>.45&&duration<2.8?12:0)+(hasRootMotion?-8:0);
    return {clip,score};
   }).sort((a,b)=>b.score-a.score);
   const selected=ranked[0];
   if(selected&&selected.clip.tracks.length&&selected.clip.duration>.12){
    runAction=mixer.clipAction(selected.clip);
    runAction.enabled=true;runAction.setLoop(THREE.LoopRepeat,Infinity);
    runAction.clampWhenFinished=false;runAction.reset();runAction.play();
    runner.userData.animationName=selected.clip.name||"unnamed";
   }
  }
  modelReady=true;
 },undefined,error=>{console.error("Runner model failed to load; using procedural runner",error);});
 const obstacles=[];let nextSpawn=1.2,elapsed=0,score=0,best=0,speed=5,paused=true,dead=false,jumpY=0,jumpV=0,grounded=true,landTimer=0,skill=.3,streak=0,view=0,laneZ=0,targetLaneZ=0;
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
  scene.add(group);addSketchOutlines(group);obstacles.push({mesh:group,x,z,w:.42,h,depth:.16,type:"pencil",passed:false});
 }
 function boxObstacle(x,z,w,h,depth,color,type){
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,depth),mat(color));mesh.position.set(x,h/2,pathZ(x)+z);scene.add(mesh);addSketchOutlines(mesh);obstacles.push({mesh,x,z,w,h,depth,type,passed:false});
 }
 function addGraphiteHatching(root,seed=1){
  // Surface-conforming graphite: strokes are interpolated on real triangles,
  // not placed on an arbitrary bounding-box plane.
  let state=(seed>>>0)||1;
  const rand=()=>{state^=state<<13;state^=state>>>17;state^=state<<5;return (state>>>0)/4294967296};
  const ink=new THREE.LineBasicMaterial({color:0x393632,transparent:true,opacity:.19,depthWrite:false,toneMapped:false});
  const vA=new THREE.Vector3(),vB=new THREE.Vector3(),vC=new THREE.Vector3();
  const nA=new THREE.Vector3(),nB=new THREE.Vector3(),nC=new THREE.Vector3();
  const p=new THREE.Vector3(),q=new THREE.Vector3(),normal=new THREE.Vector3();
  root.updateMatrixWorld(true);
  root.traverse(mesh=>{
   if(!mesh.isMesh||!mesh.geometry)return;
   const g=mesh.geometry,pos=g.attributes.position;
   if(!pos||pos.count<3)return;
   if(!g.attributes.normal)g.computeVertexNormals();
   const normals=g.attributes.normal,idx=g.index;
   const triCount=idx?idx.count/3:Math.floor(pos.count/3);
   if(!triCount)return;
   const pts=[];
   // Add detail in proportion to surface complexity, with a strict per-mesh
   // cap so mobile fill-rate and geometry costs stay predictable.
   const strokeCount=Math.min(48,Math.max(10,Math.floor(triCount*.58)));
   for(let k=0;k<strokeCount;k++){
    const tri=Math.floor(rand()*triCount),ia=idx?idx.getX(tri*3):tri*3,ib=idx?idx.getX(tri*3+1):tri*3+1,ic=idx?idx.getX(tri*3+2):tri*3+2;
    vA.fromBufferAttribute(pos,ia);vB.fromBufferAttribute(pos,ib);vC.fromBufferAttribute(pos,ic);
    nA.fromBufferAttribute(normals,ia);nB.fromBufferAttribute(normals,ib);nC.fromBufferAttribute(normals,ic);
    let u=rand()*.62+.08,v=rand()*.62+.08;if(u+v>.88){u=.88-u*.45;v=.88-v*.45}
    const w=1-u-v;
    p.copy(vA).multiplyScalar(w).addScaledVector(vB,u).addScaledVector(vC,v);
    normal.copy(nA).multiplyScalar(w).addScaledVector(nB,u).addScaledVector(nC,v).normalize();
    const edge=rand()<.5?vB.clone().sub(vA):vC.clone().sub(vA);
    edge.addScaledVector(normal,-edge.dot(normal)).normalize();
    const len=.016+rand()*.072;
    q.copy(p).addScaledVector(edge,len);
    const lift=.0025;
    p.addScaledVector(normal,lift);q.addScaledVector(normal,lift);
    pts.push(p.x,p.y,p.z,q.x,q.y,q.z);
    // A shorter, lighter second pass gives a hand-worked pencil grain.
    if(rand()<.38){
     const side=new THREE.Vector3().crossVectors(normal,edge).normalize();
     const a=p.clone().addScaledVector(side,-len*.22),b=p.clone().addScaledVector(side,len*.22);
     pts.push(a.x,a.y,a.z,b.x,b.y,b.z);
    }
   }
   const hg=new THREE.BufferGeometry();hg.setAttribute("position",new THREE.Float32BufferAttribute(pts,3));
   const strokes=new THREE.LineSegments(hg,ink);strokes.renderOrder=3;mesh.add(strokes);
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
    add(new THREE.CylinderGeometry(.23,.24,w,12,2),woodMat,0,.23,0,Math.PI/2);
    for(const side of [-1,1]){
     const end=add(new THREE.CircleGeometry(.225,18),paperMat,side*w/2,.23,0);end.rotation.y=Math.PI/2;
     const ring=add(new THREE.TorusGeometry(.15,.009,4,22),darkMat,side*(w/2+.002),.23,0);ring.rotation.y=Math.PI/2;
     const core=add(new THREE.CircleGeometry(.045,12),darkMat,side*(w/2+.003),.23,0);core.rotation.y=Math.PI/2;
     for(let k=0;k<5;k++){const yy=.23+Math.cos(k*1.256)*.18,zz=Math.sin(k*1.256)*.18;
      const grain=add(new THREE.BoxGeometry(.006,.008,.07+((k+variation)%3)*.025),darkMat,side*(w/2+.004),yy,zz);
      grain.rotation.x=k*.31;
     }
    }
  }else if(type==="rock"){
    w=.65+variation*.12;h=.5+variation*.06;depth=.65;
    const stone=add(new THREE.DodecahedronGeometry(.42+variation*.06,1),stoneMat,0,h*.45,0);
    stone.scale.set(1.05,.82,.94);
    // Broken graphite planes and a few natural fracture strokes.
    const crackPts=[];
    for(let k=0;k<5;k++){const yy=.18+((variation*7+k*13)%31)/100,zz=-.24+((variation*11+k*17)%47)/100;
     crackPts.push(-.34,yy,zz,-.18,yy+.035,zz+.025,-.08,yy+.012,zz+.08);
    }
    const cracks=new THREE.BufferGeometry();cracks.setAttribute("position",new THREE.Float32BufferAttribute(crackPts,3));
    const crackInk=new THREE.LineSegments(cracks,new THREE.LineBasicMaterial({color:0x4b4741,transparent:true,opacity:.34,depthWrite:false}));crackInk.renderOrder=3;group.add(crackInk);
  }else if(type==="crate"){
    w=.78;h=.72;depth=.72;
    add(new THREE.BoxGeometry(w,h,depth),woodMat,0,h/2,0);
    // Separate rough planks, corner joints and hand-drawn nail heads.
    for(let y=.12;y<h;y+=.19){
     add(new THREE.BoxGeometry(w-.035,.014,.012),darkMat,0,y,.367);
     add(new THREE.BoxGeometry(w-.035,.014,.012),darkMat,0,y,-.367);
    }
    for(let a=-1;a<=1;a+=2){
     add(new THREE.BoxGeometry(.075,h+.035,.78),darkMat,a*.30,h/2,0);
     add(new THREE.BoxGeometry(.78,.075,.075),darkMat,0,h/2+a*.30,0);
     for(let y of [.12,.36,.60]){const nail=add(new THREE.CircleGeometry(.018,8),paperMat,a*.30,y,.407);nail.rotation.x=0}
    }
  }else if(type==="barrier"){
    w=1.8;h=.62;depth=.28;add(new THREE.BoxGeometry(w,h,depth),paperMat,0,h/2,0);
    for(let a=-1;a<=1;a+=.5)add(new THREE.BoxGeometry(.1,h+.04,.32),darkMat,a*.65,h/2,0);
  }else if(type==="stump"){
    w=.65;h=.55;depth=.65;add(new THREE.CylinderGeometry(.25,.34,h,12,2),woodMat,0,h/2,0);
    add(new THREE.CylinderGeometry(.26,.26,.055,14),paperMat,0,h+.02,0);
    for(let r of [.075,.14,.205]){
     const growth=add(new THREE.TorusGeometry(r,.006,4,24),darkMat,0,h+.051,0);growth.rotation.x=Math.PI/2;
    }
    const splitPts=[];
    for(let k=0;k<7;k++){const t=k*Math.PI*2/7,r1=.04,r2=.23;
     splitPts.push(Math.cos(t)*r1,h+.053,Math.sin(t)*r1,Math.cos(t+.08)*r2,h+.053,Math.sin(t+.08)*r2);
    }
    const splitGeo=new THREE.BufferGeometry();splitGeo.setAttribute("position",new THREE.Float32BufferAttribute(splitPts,3));
    group.add(new THREE.LineSegments(splitGeo,new THREE.LineBasicMaterial({color:0x5b554e,transparent:true,opacity:.34,depthWrite:false})));
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
  }else if(type==="mug"){
    w=.52;h=.48;depth=.48;add(new THREE.CylinderGeometry(.22,.19,h,12),paperMat,0,h/2,0);
    const handle=add(new THREE.TorusGeometry(.14,.035,7,14),darkMat,.22,.27,0);handle.rotation.y=Math.PI/2;
  }else if(type==="kettle"){
    w=.82;h=.72;depth=.68;add(new THREE.SphereGeometry(.31,12,9),paperMat,0,.34,0);
    add(new THREE.ConeGeometry(.12,.28,8),darkMat,.34,.48,0,-Math.PI/2);
    add(new THREE.TorusGeometry(.17,.035,7,12),woodMat,-.02,.66,0);
    add(new THREE.CylinderGeometry(.045,.045,.12,8),darkMat,0,.72,0);
  }else if(type==="headphones"){
    w=.82;h=.72;depth=.34;const arc=add(new THREE.TorusGeometry(.29,.045,7,18,Math.PI),darkMat,0,.42,0);arc.rotation.z=Math.PI;
    for(let a of [-1,1])add(new THREE.BoxGeometry(.18,.25,.16),paperMat,a*.28,.25,0);
  }else if(type==="lantern"){
    w=.58;h=.92;depth=.58;add(new THREE.BoxGeometry(.42,.55,.42),paperMat,0,.36,0);
    for(let a of [-1,1])add(new THREE.BoxGeometry(.055,.68,.055),darkMat,a*.23,.36,0);
    add(new THREE.ConeGeometry(.32,.18,8),woodMat,0,.73,0);
    add(new THREE.TorusGeometry(.14,.025,6,12),darkMat,0,.91,0);
  }else if(type==="wrench"){
    w=1.15;h=.22;depth=.3;add(new THREE.BoxGeometry(.78,.12,.12),darkMat,-.12,.11,0);
    add(new THREE.TorusGeometry(.13,.045,6,12),woodMat,.42,.11,0);
    add(new THREE.BoxGeometry(.16,.12,.12),darkMat,-.56,.11,0);
  }else if(type==="toolbox"){
    w=.92;h=.55;depth=.58;add(new THREE.BoxGeometry(w*.9,.42,depth),darkMat,0,.22,0);
    add(new THREE.BoxGeometry(.36,.08,.08),woodMat,0,.49,0);
    add(new THREE.BoxGeometry(.12,.12,.04),paperMat,0,.28,.3);
  }else if(type==="frisbee"){
    w=.78;h=.14;depth=.78;add(new THREE.CylinderGeometry(.39,.35,.11,16),paperMat,0,.07,0);
    add(new THREE.TorusGeometry(.34,.025,6,16),darkMat,0,.12,0);
  }else if(type==="boot"){
    w=.72;h=.48;depth=.42;add(new THREE.BoxGeometry(.28,.32,.34),darkMat,-.12,.24,0);
    add(new THREE.BoxGeometry(.48,.14,.38),woodMat,.08,.08,.02);
    add(new THREE.BoxGeometry(.08,.24,.34),paperMat,-.22,.35,0);
  }else if(type==="birdcage"){
    w=.68;h=.9;depth=.68;add(new THREE.CylinderGeometry(.28,.28,.58,12,1,true),paperMat,0,.36,0);
    for(let a=0;a<8;a++){const t=a*Math.PI/4;add(new THREE.CylinderGeometry(.012,.012,.62,5),darkMat,Math.cos(t)*.27,.36,Math.sin(t)*.27)}
    add(new THREE.ConeGeometry(.34,.2,10),woodMat,0,.75,0);
    add(new THREE.CylinderGeometry(.32,.32,.05,12),darkMat,0,.06,0);
  }else if(type==="paintcan"){
    w=.58;h=.62;depth=.58;add(new THREE.CylinderGeometry(.26,.26,h,12),paperMat,0,h/2,0);
    add(new THREE.TorusGeometry(.26,.025,6,12),darkMat,0,h,0);
    add(new THREE.TorusGeometry(.31,.018,5,12),woodMat,0,.55,0);
  }else if(type==="dumbbell"){
    w=.82;h=.32;depth=.32;add(new THREE.CylinderGeometry(.045,.045,.48,8),woodMat,0,.16,0,Math.PI/2);
    for(let a of [-1,1])add(new THREE.CylinderGeometry(.16,.16,.16,10),darkMat,a*.28,.16,0,Math.PI/2);
  }else if(type==="wateringcan"){
    w=.82;h=.55;depth=.48;add(new THREE.BoxGeometry(.48,.38,.42),paperMat,-.04,.2,0);
    add(new THREE.TorusGeometry(.16,.035,6,12),darkMat,-.02,.42,0);
    add(new THREE.CylinderGeometry(.045,.09,.38,8),woodMat,.3,.32,0,-Math.PI/2);
    add(new THREE.CylinderGeometry(.12,.16,.08,8),darkMat,.48,.32,0,-Math.PI/2);
  }else if(type==="alarmclock"){
    w=.62;h=.72;depth=.28;add(new THREE.CylinderGeometry(.28,.28,.14,14),paperMat,0,.36,0,Math.PI/2);
    add(new THREE.TorusGeometry(.27,.025,6,14),darkMat,0,.36,.08);
    for(let a of [-1,1])add(new THREE.ConeGeometry(.1,.16,8),woodMat,a*.2,.68,0);
  }else{
    w=.95;h=.35;depth=.7;add(new THREE.BoxGeometry(w,h,depth),paperMat,0,h/2,0);
  }
  addSketchOutlines(group);addGraphiteHatching(group,variationSeed);obstacles.push({mesh:group,x,z,w:w*sx,h:h*sy,depth:depth*sz,type,passed:false});
 }
 // 100,000+ procedural combinations: 48 silhouettes, seeded scale, rotation,
 // lane placement and paired arrangements. The shuffled pool avoids short repeats.
 const obstacleCatalog=["branch","log","rock","crate","barrier","stump","bucket","cone","pencil","books","rubble","chair","umbrella","ladder","wheel","suitcase","lamp","hoop","cans","newspaper","sign","backpack","helmet","skateboard","ball","bottle","bin","stool","basket","guitar","flowerpot","toycar","foldedchair","fan","telescope","rolledpaper","mug","kettle","headphones","lantern","wrench","toolbox","frisbee","boot","birdcage","paintcan","dumbbell","wateringcan","alarmclock"];
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
 function reset(){obstacles.splice(0).forEach(o=>disposeTree(o.mesh));score=0;elapsed=0;lastStep=0;nextSpawn=.8;jumpY=0;jumpV=0;grounded=true;landTimer=0;skill=.3;streak=0;travelDistance=0;laneZ=0;targetLaneZ=0;runner.position.set(-2.25,0,0);runnerShadow.position.set(-2.17,.012,0);runnerShadow.scale.setScalar(1);runnerShadow.material.opacity=.72;runner.rotation.set(0,0,0);if(runAction)runAction.paused=false;updateTrack();dead=false;paused=false;msg.innerHTML="";setText("pause","Ⅱ")}
 function jump(){if(dead||paused){if(dead||!started){reset();started=true}return}if(grounded){jumpV=8.6;grounded=false;runner.rotation.z=-.12;tone(260,.12,"triangle",.04,180)}}
 let started=false;const msg=document.getElementById("message");
 document.getElementById("pause").addEventListener("click",()=>{if(dead||!started){reset();started=true;return}paused=!paused;setText("pause",paused?"▶":"Ⅱ");msg.textContent=paused?"ПАУЗА":""});
 document.getElementById("speed").addEventListener("input",e=>{speed=+e.target.value;setText("speedVal",speed+" / 10")});
 function steer(dir){if(dead||paused||!started)return;targetLaneZ=clamp(Math.round(targetLaneZ/1.65+dir)*1.65,-1.65,1.65)}
 window.addEventListener("keydown",e=>{if(e.code==="ArrowLeft"||e.code==="KeyA"){e.preventDefault();steer(-1)}if(e.code==="ArrowRight"||e.code==="KeyD"){e.preventDefault();steer(1)}});
 function hitRunnerScreen(x,y){
  const rect=canvas.getBoundingClientRect();
  runner.updateMatrixWorld(true);camera.updateMatrixWorld(true);
  const box=new THREE.Box3().setFromObject(runner);
  if(box.isEmpty())return false;
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity,visibleCorners=0;
  for(let a=0;a<2;a++)for(let b=0;b<2;b++)for(let c=0;c<2;c++){
   const p=new THREE.Vector3(a?box.max.x:box.min.x,b?box.max.y:box.min.y,c?box.max.z:box.min.z).project(camera);
   if(p.z< -1||p.z>1)continue;
   const sx=rect.left+(p.x+1)*.5*rect.width,sy=rect.top+(1-p.y)*.5*rect.height;
   minX=Math.min(minX,sx);maxX=Math.max(maxX,sx);minY=Math.min(minY,sy);maxY=Math.max(maxY,sy);visibleCorners++;
  }
  if(!visibleCorners)return false;
  const pad=Math.max(28,rect.width*.025);
  return x>=minX-pad&&x<=maxX+pad&&y>=minY-pad&&y<=maxY+pad;
 }
 let swipeX=null,swipeY=null,swipePointer=null;
 canvas.addEventListener("pointerdown",e=>{
  if(e.pointerType==="mouse"&&e.button!==0)return;
  swipeX=e.clientX;swipeY=e.clientY;swipePointer=e.pointerId;
  try{canvas.setPointerCapture(e.pointerId)}catch(_){}
 });
 canvas.addEventListener("pointerup",e=>{
  if(swipeX===null||e.pointerId!==swipePointer)return;
  const dx=e.clientX-swipeX,dy=e.clientY-swipeY;
  if(Math.hypot(dx,dy)>26){
   if(Math.abs(dx)>Math.abs(dy)*.85)steer(dx>0?1:-1);
  }else if(started&&!paused&&!dead){
   if(hitRunnerScreen(e.clientX,e.clientY))jump();
  }
  swipeX=null;swipeY=null;swipePointer=null;
 });
 const clearPointer=e=>{
  if(e.pointerId===swipePointer){swipeX=null;swipeY=null;swipePointer=null}
 };
 canvas.addEventListener("pointercancel",clearPointer);
 canvas.addEventListener("lostpointercapture",clearPointer);
 msg.addEventListener("click",e=>{if(e.target&&e.target.id==="play"){reset();started=true}});
 document.getElementById("sound").addEventListener("click",e=>{soundEnabled=!soundEnabled;e.currentTarget.textContent=soundEnabled?"♪":"×";if(soundEnabled){audioReady();tone(520,.07,"sine",.025)}});
 document.querySelectorAll("[data-view]").forEach((b,i)=>b.addEventListener("click",()=>{view=i;document.querySelectorAll("[data-view]").forEach(x=>x.classList.toggle("active",x===b))}));
 window.addEventListener("keydown",e=>{if(e.code==="Escape"&&started&&!dead){paused=!paused;setText("pause",paused?"▶":"Ⅱ");msg.textContent=paused?"ПАУЗА":""}});
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
   if(mixer){
    // Remove last frame's procedural offsets before evaluating the authored clip.
    // This prevents unkeyed bones from accumulating rotation over long runs.
    if(runner.userData.jumpBones)runner.userData.jumpBones.forEach(item=>{
     if(item.offsetX){item.bone.rotation.x-=item.offsetX;item.offsetX=0}
    });
    mixer.timeScale=.35+speed*.19;mixer.update(dt);
    // Small stride accents supplement rigs with stiff feet or weak arm swing.
    if(runner.userData.jumpBones&&grounded){
     const phase=elapsed*velocity*1.8;
     runner.userData.jumpBones.forEach(item=>{
      const side=item.side||1,wave=Math.sin(phase+(side<0?0:Math.PI));
      let offset=0;
      if(item.joint==="thigh")offset=wave*.075;
      else if(item.joint==="calf")offset=Math.max(0,-wave)*.105*side;
      else if(item.joint==="upperArm")offset=-wave*.065;
      else if(item.joint==="forearm")offset=Math.max(0,wave)*.035;
      else if(item.joint==="foot")offset=-wave*.095;
      else if(item.joint==="spine")offset=Math.sin(phase*2)*.018;
      item.bone.rotation.x+=offset;item.offsetX=offset;
     });
    }
   }
   else if(runner.userData.limbs&&runner.userData.limbs[0]?.leg?.parent){
    const p=elapsed*velocity*1.8,cycle=Math.sin(p),bob=Math.abs(Math.sin(p*2));
    runner.userData.limbs.forEach(l=>{
     const swing=Math.sin(p+(l.side<0?0:Math.PI));
     l.leg.rotation.x=swing*.78;
     l.arm.rotation.x=-swing*.72;
     l.hand.position.set(l.side*.34,.88+Math.sin(p+(l.side<0?0:Math.PI))*.055,Math.cos(p+(l.side<0?0:Math.PI))*.045);
     l.foot.rotation.x=swing*.22;
    });
    if(runner.userData.torso){runner.userData.torso.position.y=1.12+bob*.025;runner.userData.torso.rotation.z=cycle*.018}
    if(runner.userData.head)runner.userData.head.rotation.z=-cycle*.012;
   }
   else if(runner.userData.model){const p=elapsed*velocity*3.2;runner.userData.model.position.y=runner.userData.modelBaseY+Math.abs(Math.sin(p))*.025;runner.userData.model.rotation.z=Math.sin(p)*.018}
   if(!grounded){
    jumpV-=21*dt;jumpY+=jumpV*dt;
    if(jumpY<=0){jumpY=0;jumpV=0;grounded=true;landTimer=.24;tone(92,.07,"triangle",.022,-24)}
   }
   // Keep the authored rig updating so each frame starts from its clean
   // keyframed pose before the procedural airborne joint offsets are layered on.
   if(runAction)runAction.paused=false;
   runner.rotation.z=grounded?0:clamp(-jumpV*.018,-.18,.16);
   if(!grounded){
    const tuck=clamp(jumpY*.34,0,.48);
    if(runner.userData.limbs){
     runner.userData.limbs.forEach(l=>{
      l.leg.rotation.x=(l.side<0?1:-1)*(.42+tuck);
      l.arm.rotation.x=(l.side<0?-1:1)*(.62+tuck*.35);
      l.foot.rotation.x=-.18-tuck*.25;
     });
    }
    // Add a compact airborne pose to the downloaded rig as well as the fallback.
    // Mixer updates happen earlier in the frame, so these offsets layer over its
    // current keyframed rotations and disappear naturally when the run resumes.
    if(runner.userData.jumpBones){
     const phase=clamp(jumpY/.85,0,1);
     for(const item of runner.userData.jumpBones){
      const sign=item.side||1, b=item.bone;
      let offset=0;
      if(item.joint==="thigh")offset=sign*(.22+phase*.38);
      else if(item.joint==="calf")offset=-sign*(.18+phase*.42);
      else if(item.joint==="upperArm")offset=-sign*(.16+phase*.28);
      else if(item.joint==="forearm")offset=sign*(.12+phase*.2);
      else if(item.joint==="spine")offset=-.035-phase*.045;
      b.rotation.x+=offset;item.offsetX=offset;
     }
    }
   }
   // Brief compression on touchdown, with a smooth return to the run pose.
   if(landTimer>0){
    landTimer=Math.max(0,landTimer-dt);
    const crouch=Math.sin((landTimer/.24)*Math.PI)*.12;
    runner.rotation.x=-crouch*.22;
    if(runner.userData.limbs)runner.userData.limbs.forEach(l=>{
     l.leg.rotation.x+=(l.side<0?1:-1)*crouch;
     l.arm.rotation.x-=(l.side<0?1:-1)*crouch*.45;
    });
    if(runner.userData.jumpBones)runner.userData.jumpBones.forEach(item=>{
     const sign=item.side||1;let offset=0;
     if(item.joint==="thigh")offset=sign*crouch*.55;
     else if(item.joint==="calf")offset=-sign*crouch*.35;
     else if(item.joint==="spine")offset=crouch*.22;
     item.bone.rotation.x+=offset;item.offsetX+=offset;
    });
   }else if(grounded){runner.rotation.x=THREE.MathUtils.damp(runner.rotation.x,0,12,dt)}
   if(grounded&&elapsed-lastStep>Math.max(.22,.48/(.5+speed*.14))){tone(68,.045,"sine",.012,-12);lastStep=elapsed}
   runner.position.y=jumpY;runner.position.x=-2.25;
   runnerShadow.position.x=runner.position.x+.08;runnerShadow.position.z=laneZ+pathZ(-2.25);runnerShadow.scale.setScalar(1-Math.min(.42,jumpY*.12));runnerShadow.material.opacity=.72*(1-Math.min(.72,jumpY*.22));

   nextSpawn-=dt;if(nextSpawn<=0)spawn();

   for(let i=obstacles.length-1;i>=0;i--){const o=obstacles[i];o.x-=velocity*dt;o.mesh.position.x=o.x;o.mesh.position.z=pathZ(o.x)+o.z;
    if(!o.passed&&o.x< -2.7){o.passed=true;streak++;aiDirector.recordPass()}
    // Broad phase first, then test the real transformed 3D bounds.
    const nearX=Math.abs(o.x+2.25)<(o.w*.5+.48),nearLane=Math.abs(o.z-laneZ)<((o.depth||.7)*.5+.62);
    if(nearX&&nearLane){
     runner.updateMatrixWorld(true);o.mesh.updateMatrixWorld(true);
     const runnerBounds=new THREE.Box3().setFromObject(runner);
     const obstacleBounds=new THREE.Box3().setFromObject(o.mesh);
     obstacleBounds.expandByVector(new THREE.Vector3(.045,.025,.045));
     if(runnerBounds.intersectsBox(obstacleBounds)){
      dead=true;landTimer=0;impactSound();aiDirector.recordHit();
      // A readable impact pose: pitch forward and fold the limbs rather than
      // leaving the runner frozen in a perfectly upright running silhouette.
      runner.rotation.x=-.16;runner.rotation.z=.24;
      if(runner.userData.limbs)runner.userData.limbs.forEach(l=>{
       l.leg.rotation.x=(l.side<0?1:-1)*.72;
       l.arm.rotation.x=(l.side<0?-1:1)*1.05;
       l.foot.rotation.x=-.28;
      });
      if(runner.userData.jumpBones)runner.userData.jumpBones.forEach(item=>{
       const sign=item.side||1;
       if(item.joint==="thigh")item.bone.rotation.x+=sign*.42;
       else if(item.joint==="calf")item.bone.rotation.x-=sign*.3;
       else if(item.joint==="upperArm")item.bone.rotation.x-=sign*.62;
       else if(item.joint==="forearm")item.bone.rotation.x+=sign*.38;
       else if(item.joint==="spine")item.bone.rotation.x-=.12;
      });
      best=Math.max(best,Math.floor(score));
      try{localStorage.setItem("rm3dBest",best)}catch(e){}
      msg.innerHTML="СТОЛКНОВЕНИЕ<br>СЧЁТ: "+Math.floor(score)+" · РЕКОРД: "+best+"<br><button id='retry'>ЕЩЁ РАЗ</button>";
      document.getElementById("retry").onclick=()=>{reset();started=true};break;
     }
    }
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
