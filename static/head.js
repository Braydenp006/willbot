import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const box = document.getElementById("head");
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(800, 800);
box.appendChild(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 3));

// The head sways around this point; berries are added to it too
const pivot = new THREE.Group();
scene.add(pivot);

let size = null;
const jawMeshes = [];

new GLTFLoader().load("/static/will.glb", (gltf) => {
  const model = gltf.scene;
  const bounds = new THREE.Box3().setFromObject(model);
  model.position.sub(bounds.getCenter(new THREE.Vector3()));
  size = bounds.getSize(new THREE.Vector3());
  camera.position.z = size.y * 2.2;
  pivot.add(model);
  model.traverse((obj) => {
    if (obj.morphTargetDictionary?.jawOpen !== undefined) jawMeshes.push(obj);
  });
});

function setJaw(amount) {
  for (const m of jawMeshes) {
    m.morphTargetInfluences[m.morphTargetDictionary.jawOpen] = amount;
  }
}
window.setJaw = setJaw;

// --- Berries ---
const MOUTH = new THREE.Vector3(0, -0.22, 0.45);  // as fractions of the head's size
const START = new THREE.Vector3(0.5, -0.9, 0.6);
const berryGeo = new THREE.IcosahedronGeometry(1, 0);
const berryMat = new THREE.MeshStandardMaterial({ color: 0x8e1b3a, flatShading: true, roughness: 1 });
let berry = null;
let flight = 0;
let chewing = 0;

const mmm = new Audio("/voicelines/mmm.wav");
const greeting = new Audio("/voicelines/zara.wav");

function playVoiceline(vLine) {
  vLine.currentTime  = 0;
  vLine.play().catch((e) => console.error("voiceline failed:", e));
}

box.addEventListener("pointerdown", () => {
  audioCtx.resume();
  if (!size || berry) return;
  berry = new THREE.Mesh(berryGeo, berryMat);
  berry.scale.setScalar(size.y * 0.04);
  pivot.add(berry);
  flight = 0;
});

// --- Every frame ---
const samples = new Float32Array(512);
const GAIN = 10;
const SMOOTH = 0.8;
let jaw = 0;
let last = 0;
// Retro talking: jaw snaps between a few positions, updated a few times a second
const JAW_STEPS = 6;
const JAW_FPS = 12;
let talkJaw = 0;
let nextTalk = 0;

renderer.setAnimationLoop((time) => {
  const t = time / 1000;
  const dt = t - last;
  last = t;

  // Idle: slow sway, slight nod, gentle bob
  pivot.rotation.y = Math.sin(t * 0.6) * 0.15;
  pivot.rotation.x = Math.sin(t * 0.4) * 0.05;
  if (size) pivot.position.y = Math.sin(t * 1.2) * size.y * 0.02;

  // Feeding
  let feedJaw = 0;
  if (berry) {
    flight = Math.min(flight + dt * 1.5, 1);
    const from = START.clone().multiply(size);
    const to = MOUTH.clone().multiply(size);
    berry.position.lerpVectors(from, to, flight);
    berry.position.y += Math.sin(flight * Math.PI) * size.y * 0.2;
    feedJaw = flight;
    if (flight === 1) {
      pivot.remove(berry);
      berry = null;
      chewing = 1.5;
      playVoiceline(mmm);
    }
  } else if (chewing > 0) {
    chewing -= dt;
    feedJaw = 0.3 + 0.2 * Math.sin(t * 18);
  }

  // Speaking
  if (window.analyser && t >= nextTalk) {
    nextTalk = t + 1 / JAW_FPS;
    window.analyser.getFloatTimeDomainData(samples);
    let sum = 0;
    for (const s of samples) sum += s * s;
    const level = Math.min(Math.sqrt(sum / samples.length) * GAIN, 1);
    talkJaw = Math.round(level * JAW_STEPS) / JAW_STEPS;
  }

  jaw += (Math.max(talkJaw, feedJaw) - jaw) * SMOOTH;
  setJaw(jaw);
  renderer.render(scene, camera);
});
