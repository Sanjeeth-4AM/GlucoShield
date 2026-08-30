import React, { useEffect, useRef } from "react";

export function MetabolicShaderBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    if (!gl) return;

    function syncSize() {
      const w = window.innerWidth || 1280;
      const h = window.innerHeight || 720;
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
    }
    syncSize();
    window.addEventListener("resize", syncSize);

    const vs = `
      attribute vec2 a_position;
      varying vec2 v_texCoord;
      void main() {
        v_texCoord = a_position * 0.5 + 0.5;
        gl_Position = vec4(a_position, 0.0, 1.0);
      }
    `;

    const fs = `
      precision highp float;
      varying vec2 v_texCoord;
      uniform float u_time;
      uniform vec2 u_resolution;

      float noise(vec2 p) {
        return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
      }

      void main() {
        vec2 uv = v_texCoord;
        
        // Deep Space Navy base
        vec3 baseColor = vec3(0.047, 0.075, 0.141);
        
        // Pulsing core intelligence
        float pulse = sin(u_time * 0.35) * 0.5 + 0.5;
        float dist = length(uv - vec2(0.5, 0.5));
        float glow = smoothstep(1.0, 0.0, dist);
        
        vec3 accentColor = vec3(0.0, 0.55, 0.65); // Cyan-Teal
        vec3 finalColor = baseColor + (accentColor * glow * 0.12 * pulse);
        
        // Sub-pixel data flux noise
        float n = noise(uv * 80.0 + u_time * 0.08);
        finalColor += vec3(0.0, 0.08, 0.12) * n * 0.025;
        
        // Technical grid lines
        vec2 grid = fract(uv * 32.0);
        float gridLine = smoothstep(0.985, 1.0, grid.x) + smoothstep(0.985, 1.0, grid.y);
        finalColor += vec3(0.0, 0.25, 0.35) * gridLine * 0.04;

        gl_FragColor = vec4(finalColor, 1.0);
      }
    `;

    function createShader(type, src) {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    }

    const prog = gl.createProgram();
    gl.attachShader(prog, createShader(gl.VERTEX_SHADER, vs));
    gl.attachShader(prog, createShader(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog);
    gl.useProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);

    const pos = gl.getAttribLocation(prog, "a_position");
    gl.enableVertexAttribArray(pos);
    gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);

    const uTime = gl.getUniformLocation(prog, "u_time");
    const uRes = gl.getUniformLocation(prog, "u_resolution");

    let animId;
    function render(t) {
      gl.viewport(0, 0, canvas.width, canvas.height);
      if (uTime) gl.uniform1f(uTime, t * 0.001);
      if (uRes) gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      animId = requestAnimationFrame(render);
    }
    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", syncSize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none z-0 opacity-40 mix-blend-screen"
    />
  );
}
