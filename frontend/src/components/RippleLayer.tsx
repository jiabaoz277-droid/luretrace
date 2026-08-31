"use client";

import { useEffect, useRef } from "react";

/**
 * 鼠标涟漪层：鼠标/手指划过时，在水面背景上泛起扩散涟漪 + 跟随光晕。
 * 纯 canvas + pointer-events:none，不拦截任何点击交互。
 */
export function RippleLayer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    type Ripple = { x: number; y: number; r: number; a: number };
    const ripples: Ripple[] = [];
    let lastX = -1e4;
    let lastY = -1e4;
    const light = { x: window.innerWidth / 2, y: window.innerHeight * 0.4 };
    const target = { x: light.x, y: light.y };
    let raf = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const spawn = (x: number, y: number) => {
      if (Math.hypot(x - lastX, y - lastY) < 26) return; // 距离节流：一圈圈而非糊成一片
      lastX = x;
      lastY = y;
      if (ripples.length > 46) ripples.shift();
      ripples.push({ x, y, r: 8, a: 0.5 });
      target.x = x;
      target.y = y;
    };

    const onMove = (e: MouseEvent) => spawn(e.clientX, e.clientY);
    const onTouch = (e: TouchEvent) => {
      const t = e.touches?.[0];
      if (t) spawn(t.clientX, t.clientY);
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("touchmove", onTouch, { passive: true });

    let last = performance.now();
    const frame = (now: number) => {
      const dt = Math.min((now - last) / 16.666, 3);
      last = now;
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

      // 跟随指针的柔和光晕（水面反光）
      light.x += (target.x - light.x) * 0.12;
      light.y += (target.y - light.y) * 0.12;
      const g = ctx.createRadialGradient(light.x, light.y, 0, light.x, light.y, 170);
      g.addColorStop(0, "rgba(255,224,170,0.09)");
      g.addColorStop(1, "rgba(255,224,170,0)");
      ctx.fillStyle = g;
      ctx.fillRect(light.x - 170, light.y - 170, 340, 340);

      // 扩散涟漪（椭圆，模拟俯视水面）
      for (let i = ripples.length - 1; i >= 0; i -= 1) {
        const rp = ripples[i];
        rp.r += 1.7 * dt;
        rp.a -= 0.013 * dt;
        if (rp.a <= 0 || rp.r > 150) {
          ripples.splice(i, 1);
          continue;
        }
        const ry = rp.r * 0.5;
        ctx.beginPath();
        ctx.ellipse(rp.x, rp.y, rp.r, ry, 0, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255,255,255,${rp.a.toFixed(3)})`;
        ctx.lineWidth = 1.4;
        ctx.stroke();
        ctx.beginPath();
        ctx.ellipse(rp.x, rp.y, rp.r * 0.58, ry * 0.58, 0, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255,214,160,${(rp.a * 0.8).toFixed(3)})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("touchmove", onTouch);
    };
  }, []);

  return <canvas ref={canvasRef} className="ripple-canvas" aria-hidden="true" />;
}
