            let remaining = 12000, nodes = 0, truncated = false;
            const seen = new WeakSet();
            function cut(s, limit) {
                s = String(s);
                const n = Math.max(0, Math.min(limit, remaining));
                if (s.length > n) truncated = true;
                const out = s.slice(0, n); remaining -= out.length;
                return out;
            }
            function preview(v, depth) {
                if (++nodes > 500 || remaining <= 0) { truncated = true; return null; }
                if (v === null) return null;
                if (typeof v === 'string') return cut(v, 1000);
                if (typeof v === 'boolean') return v;
                if (typeof v === 'number') return Number.isFinite(v) ? v : null;
                if (typeof v === 'bigint') return cut(v.toString(), 100);
                if (typeof v !== 'object') { truncated = true; return null; }
                if (depth >= 5 || seen.has(v)) { truncated = true; return null; }
                seen.add(v);
                if (Array.isArray(v)) {
                    const out = [], count = Math.min(v.length, 40);
                    if (v.length > count) truncated = true;
                    for (let i=0; i<count && remaining>0 && nodes<500; i++) out.push(preview(v[i], depth+1));
                    if (out.length < v.length) truncated = true;
                    return out;
                }
                const out = Object.create(null);
                let count = 0;
                for (const key in v) {
                    if (!Object.prototype.hasOwnProperty.call(v,key)) continue;
                    if (count++ >= 40 || remaining<=0 || nodes>=500) { truncated=true; break; }
                    const d = Object.getOwnPropertyDescriptor(v,key);
                    if (!d || !('value' in d)) { truncated=true; continue; }
                    out[cut(key,128)] = preview(d.value, depth+1);
                }
                return out;
            }
            const value = preview(source,0);
            return {value, truncated, limits:{textChars:12000,stringChars:1000,items:40,depth:5,nodes:500},
                    hint:truncated ? '结果为截断预览，不代表完整数据。只读提取请限定字段，并按数组索引/文字偏移显式分段；不要重放有副作用的原脚本。' : ''};
        })()