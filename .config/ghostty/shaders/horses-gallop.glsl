// horses-gallop.glsl
// Galloping horses with show jumping — they arc over verticals and oxers.

float sdCapsule(vec2 p, vec2 a, vec2 b, float r) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h) - r;
}

// jmp: 0=galloping, 1=jump apex (legs tucked in bascule, neck stretched forward)
float horseSDF(vec2 p, float gait, float jmp) {
    float d = 1e9;

    // Body
    d = min(d, sdCapsule(p, vec2(-0.32, 0.00), vec2(0.20, 0.05), 0.20));
    // Hindquarters
    d = min(d, sdCapsule(p, vec2(-0.38, 0.08), vec2(-0.16, 0.22), 0.14));
    // Withers
    d = min(d, sdCapsule(p, vec2( 0.08, 0.10), vec2( 0.20, 0.24), 0.13));
    // Neck — stretches forward and lowers on jump
    float nfwd = jmp * 0.14;
    float nlwr = jmp * 0.10;
    d = min(d, sdCapsule(p, vec2(0.16, 0.20), vec2(0.36 + nfwd, 0.50 - nlwr), 0.09));
    // Head
    d = min(d, sdCapsule(p, vec2(0.36 + nfwd, 0.50 - nlwr), vec2(0.54 + nfwd, 0.44 - nlwr), 0.11));
    // Muzzle
    d = min(d, sdCapsule(p, vec2(0.50 + nfwd, 0.44 - nlwr), vec2(0.64 + nfwd, 0.37 - nlwr * 0.7), 0.07));
    // Ear
    d = min(d, sdCapsule(p, vec2(0.40 + nfwd, 0.57 - nlwr), vec2(0.45 + nfwd, 0.67 - nlwr), 0.04));
    // Mane
    d = min(d, sdCapsule(p, vec2(0.20, 0.34), vec2(0.36 + nfwd, 0.52 - nlwr * 0.8), 0.035));

    // Tail — wave dampens at jump apex
    float tw = sin(gait * 1.4) * 0.14 * (1.0 - jmp * 0.8);
    d = min(d, sdCapsule(p, vec2(-0.38, 0.14), vec2(-0.56 + tw * 0.2, 0.36 + tw), 0.05));
    d = min(d, sdCapsule(p, vec2(-0.56 + tw * 0.2, 0.36 + tw),
                            vec2(-0.50 + tw * 0.1, 0.22 + tw * 0.5), 0.04));

    float sw = 0.55;
    float ll = 0.38;
    float lr = 0.048;

    // At jump apex, tuck: front legs fold forward-up, back legs fold back-up (bascule)
    float a1 = mix(sin(gait         ) * sw, 2.2, jmp);
    float a2 = mix(sin(gait + 3.14159) * sw, 2.2, jmp);
    float a3 = mix(sin(gait + 1.5708) * sw, 3.9, jmp);
    float a4 = mix(sin(gait + 4.7124) * sw, 3.9, jmp);

    vec2 fr = vec2( 0.18, -0.16);
    vec2 fl = vec2( 0.11, -0.16);
    vec2 br = vec2(-0.20, -0.16);
    vec2 bl = vec2(-0.27, -0.16);

    d = min(d, sdCapsule(p, fr, fr + vec2(sin(a1), -cos(a1)) * ll, lr));
    d = min(d, sdCapsule(p, fl, fl + vec2(sin(a2), -cos(a2)) * ll, lr));
    d = min(d, sdCapsule(p, br, br + vec2(sin(a3), -cos(a3)) * ll, lr));
    d = min(d, sdCapsule(p, bl, bl + vec2(sin(a4), -cos(a4)) * ll, lr));

    return d;
}

// Parabolic lift arc: peaks at 1 when hx==jx, falls to 0 outside ±radius
float jumpArc(float hx, float jx, float radius) {
    float t = (hx - jx) / radius;
    return max(0.0, 1.0 - t * t);
}

// SDF for a horizontal jump rail (very thin capsule)
float railSDF(vec2 fc, float x0, float x1, float y, float r) {
    return sdCapsule(fc, vec2(x0, y), vec2(x1, y), r);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec4 term = texture(iChannel0, uv);
    vec3 color = term.rgb;

    float W = iResolution.x;
    float H = iResolution.y;

    // Render the (bottom-anchored) scene in the TOP 28% of the screen.
    // Trick: only run for screen uv.y < 0.28, then shift world coords up by 0.72
    // so all the existing "bottom" checks (uv.y >= 0.86, etc.) fire correctly.
    if (uv.y >= 0.28) {
        fragColor = vec4(color, term.a);
        return;
    }
    fragCoord.y += 0.72 * H;
    uv.y       += 0.72;

    // === GRASS LAYER: bottom 14%, gameboy pixel tiles ===
    if (uv.y >= 0.86) {
        float px  = 4.0;
        float col = floor(fragCoord.x / px);
        float fromBottom = H - fragCoord.y;

        float wave  = sin(col * 0.20 + iTime * 2.0) * 0.5 + 0.5;
        float bladeH = px * (2.0 + floor(wave * 3.0));

        if (fromBottom < bladeH) {
            float t = fromBottom / bladeH;
            vec3 tip  = vec3(0.42, 0.72, 0.16);
            vec3 mid  = vec3(0.22, 0.50, 0.08);
            vec3 base = vec3(0.10, 0.30, 0.04);
            vec3 gc = t > 0.55 ? mix(mid, tip, (t - 0.55) / 0.45)
                               : mix(base, mid, t / 0.55);
            color = mix(color, gc, 0.48);
        }
    }

    // === JUMP OBSTACLES (rendered in bottom 25%) ===
    float jx1 = W * 0.300;   // vertical
    float jx2 = W * 0.685;   // oxer

    if (uv.y >= 0.75) {
        float rRail = 2.0;
        float rStd  = 2.5;
        float hw    = W * 0.022;   // half-span of each fence
        float ry1   = H * 0.938;   // rail height for vertical (~6% above ground)
        float ry2   = H * 0.935;   // front rail of oxer
        float sp    = W * 0.014;   // oxer spread

        // Stripe pattern: diagonal bands along each element
        float stripe = mod(floor((fragCoord.x - fragCoord.y) / 10.0), 2.0);
        vec3 colA = vec3(0.80, 0.12, 0.06);   // red
        vec3 colB = vec3(0.92, 0.88, 0.80);   // cream/white
        vec3 stdColor = vec3(0.55, 0.38, 0.18); // wooden standard

        // --- Vertical: one rail + two standards ---
        float dV = 1e9;
        dV = min(dV, railSDF(fragCoord, jx1 - hw, jx1 + hw, ry1, rRail));   // rail
        dV = min(dV, sdCapsule(fragCoord, vec2(jx1 - hw, H), vec2(jx1 - hw, ry1), rStd)); // left std
        dV = min(dV, sdCapsule(fragCoord, vec2(jx1 + hw, H), vec2(jx1 + hw, ry1), rStd)); // right std

        if (dV < 0.0) {
            // Rail gets diagonal stripes; standards get wood color
            bool onRail = railSDF(fragCoord, jx1 - hw, jx1 + hw, ry1, rRail) < 0.0;
            color = mix(color, onRail ? (stripe < 1.0 ? colA : colB) : stdColor, 0.82);
        }

        // --- Oxer: two rails + four standards ---
        float dO = 1e9;
        float rx1 = jx2 - sp;  float rx2 = jx2 + sp;
        dO = min(dO, railSDF(fragCoord, rx1 - hw, rx1 + hw, ry2 + 5.0, rRail));   // back rail (lower)
        dO = min(dO, railSDF(fragCoord, rx2 - hw, rx2 + hw, ry2,       rRail));   // front rail (higher)
        dO = min(dO, sdCapsule(fragCoord, vec2(rx1 - hw, H), vec2(rx1 - hw, ry2 + 5.0), rStd));
        dO = min(dO, sdCapsule(fragCoord, vec2(rx1 + hw, H), vec2(rx1 + hw, ry2 + 5.0), rStd));
        dO = min(dO, sdCapsule(fragCoord, vec2(rx2 - hw, H), vec2(rx2 - hw, ry2), rStd));
        dO = min(dO, sdCapsule(fragCoord, vec2(rx2 + hw, H), vec2(rx2 + hw, ry2), rStd));

        if (dO < 0.0) {
            bool onRail = (railSDF(fragCoord, rx1-hw, rx1+hw, ry2+5.0, rRail) < 0.0 ||
                           railSDF(fragCoord, rx2-hw, rx2+hw, ry2,     rRail) < 0.0);
            vec3 oxStripe = stripe < 1.0 ? vec3(0.10, 0.32, 0.70) : colB;  // blue/white oxer
            color = mix(color, onRail ? oxStripe : stdColor, 0.82);
        }
    }

    // === HORSE LAYER: bottom 28% (extra height for jump arcs) ===
    if (uv.y >= 0.72) {
        float margin = H * 0.30;
        float total  = W + margin;
        float gK     = 0.055;
        float liftMax = H * 0.045;   // maximum lift height at apex

        float h1s = H * 0.072; float h1x = W - mod(iTime * 0.058 * W + 0.00 * total, total); float h1yG = H * 0.925;
        float h2s = H * 0.054; float h2x = W - mod(iTime * 0.090 * W + 0.42 * total, total); float h2yG = H * 0.920;
        float h3s = H * 0.042; float h3x = W - mod(iTime * 0.041 * W + 0.70 * total, total); float h3yG = H * 0.915;
        float h4s = H * 0.062; float h4x = W - mod(iTime * 0.074 * W + 0.86 * total, total); float h4yG = H * 0.922;

        // Each horse lifts over whichever fence it's currently nearest
        float arc1 = max(jumpArc(h1x, jx1, h1s * 3.0), jumpArc(h1x, jx2, h1s * 3.0));
        float arc2 = max(jumpArc(h2x, jx1, h2s * 3.0), jumpArc(h2x, jx2, h2s * 3.0));
        float arc3 = max(jumpArc(h3x, jx1, h3s * 3.0), jumpArc(h3x, jx2, h3s * 3.0));
        float arc4 = max(jumpArc(h4x, jx1, h4s * 3.0), jumpArc(h4x, jx2, h4s * 3.0));

        float h1y = h1yG - liftMax * arc1;
        float h2y = h2yG - liftMax * arc2;
        float h3y = h3yG - liftMax * arc3;
        float h4y = h4yG - liftMax * arc4;

        float d = 1e9;
        vec2 p;
        // Flip y (Ghostty y-down) and x (horse faces direction of travel)
        p = (fragCoord - vec2(h1x, h1y)) / h1s; p.y = -p.y; p.x = -p.x; d = min(d, horseSDF(p, -h1x * gK, arc1) * h1s);
        p = (fragCoord - vec2(h2x, h2y)) / h2s; p.y = -p.y; p.x = -p.x; d = min(d, horseSDF(p, -h2x * gK, arc2) * h2s);
        p = (fragCoord - vec2(h3x, h3y)) / h3s; p.y = -p.y; p.x = -p.x; d = min(d, horseSDF(p, -h3x * gK, arc3) * h3s);
        p = (fragCoord - vec2(h4x, h4y)) / h4s; p.y = -p.y; p.x = -p.x; d = min(d, horseSDF(p, -h4x * gK, arc4) * h4s);

        float horseAlpha = (1.0 - smoothstep(-1.5, 1.5, d)) * 0.22;
        color = mix(color, vec3(0.22, 0.10, 0.03), horseAlpha);
    }

    fragColor = vec4(color, term.a);
}
