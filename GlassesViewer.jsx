import React, { useRef, useEffect } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";

export default function GlassesViewer({ glbUrl }) {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!glbUrl) return;
    const mount = mountRef.current;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, mount.clientWidth / mount.clientHeight, 0.1, 1000);
    camera.position.set(0, 0, 2);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    const light = new THREE.HemisphereLight(0xffffff, 0x444444);
    light.position.set(0, 20, 0);
    scene.add(light);

    const loader = new GLTFLoader();
    let model = null;
    loader.load(glbUrl, (gltf) => {
      model = gltf.scene;
      model.scale.set(1,1,1);
      scene.add(model);
    }, undefined, (err) => console.error(err));

    const controls = new THREE.OrbitControls(camera, renderer.domElement);

    function animate() {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    }
    animate();

    const handleResize = () => {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      renderer.dispose();
      if (model) scene.remove(model);
      mount.removeChild(renderer.domElement);
    };
  }, [glbUrl]);

  return <div ref={mountRef} style={{ width: "100%", height: "500px" }} />;
}
