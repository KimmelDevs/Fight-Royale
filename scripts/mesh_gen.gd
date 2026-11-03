extends RefCounted
## Procedural meshes for cloth and hair, with UVs and Godot's clockwise front-face winding.


## Adds one triangle, flipping its winding so the front face points along `expected`.
static func _tri(st: SurfaceTool, p: Array, n: Array, uv: Array, expected: Vector3) -> void:
	var order := [0, 1, 2]
	# Godot treats clockwise (as seen by the viewer) as front, so the geometric
	# cross product of a front face points away from the viewer.
	if (p[1] - p[0]).cross(p[2] - p[0]).dot(expected) > 0.0:
		order = [0, 2, 1]
	for i: int in order:
		st.set_normal(n[i])
		st.set_uv(uv[i])
		st.add_vertex(p[i])


## Cone-shaped sheet hanging down from y = 0 (skirts, sleeves, capes).
## Angles are radians around Y with 0 = +Z (front). UV.x runs a0 -> a1, UV.y runs top -> hem.
## `ruffle_amp`/`ruffle_freq` make a wavy hem; `extra_len(a)` lengthens the hem per angle.
static func cone_sheet(top_r: float, bottom_r: float, height: float, a0 := 0.0, a1 := TAU,
		seg_a := 32, seg_v := 6, ruffle_amp := 0.0, ruffle_freq := 0.0,
		extra_len := Callable()) -> ArrayMesh:
	var closed := is_equal_approx(a1 - a0, TAU)
	var grid: Array = []
	for i in seg_a + 1:
		var a := lerpf(a0, a1, float(i) / seg_a)
		var length := height + (float(extra_len.call(a)) if extra_len.is_valid() else 0.0)
		var col: Array[Vector3] = []
		for j in seg_v + 1:
			var v := float(j) / seg_v
			var r := lerpf(top_r, bottom_r, v) + ruffle_amp * sin(a * ruffle_freq) * v * v
			col.append(Vector3(sin(a) * r, -v * length, cos(a) * r))
		grid.append(col)

	var normals: Array = []
	for i in seg_a + 1:
		var a := lerpf(a0, a1, float(i) / seg_a)
		var radial := Vector3(sin(a), 0.0, cos(a))
		var col: Array[Vector3] = []
		for j in seg_v + 1:
			var ip := i + 1
			var im := i - 1
			if closed:
				ip = 1 if i == seg_a else ip
				im = seg_a - 1 if i == 0 else im
			ip = mini(ip, seg_a)
			im = maxi(im, 0)
			var du: Vector3 = grid[ip][j] - grid[im][j]
			var dv: Vector3 = grid[i][mini(j + 1, seg_v)] - grid[i][maxi(j - 1, 0)]
			var n := du.cross(dv).normalized()
			if n.dot(radial) < 0.0:
				n = -n
			col.append(n)
		normals.append(col)

	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in seg_a:
		for j in seg_v:
			var ids := [Vector2i(i, j), Vector2i(i + 1, j), Vector2i(i, j + 1), Vector2i(i + 1, j + 1)]
			var p: Array = []
			var n: Array = []
			var uv: Array = []
			for id: Vector2i in ids:
				p.append(grid[id.x][id.y])
				n.append(normals[id.x][id.y])
				uv.append(Vector2(float(id.x) / seg_a, float(id.y) / seg_v))
			var expected: Vector3 = (n[0] + n[3]).normalized()
			_tri(st, [p[0], p[1], p[3]], [n[0], n[1], n[3]], [uv[0], uv[1], uv[3]], expected)
			_tri(st, [p[0], p[3], p[2]], [n[0], n[3], n[2]], [uv[0], uv[3], uv[2]], expected)
	return st.commit()


## Tapered, flattened hair lock along a quadratic bezier p0 -> p1 -> p2.
## The flat face points away from `center` (the head center), so locks hug the head.
static func strand(p0: Vector3, p1: Vector3, p2: Vector3, width: float, thick: float,
		center := Vector3.ZERO, seg := 8, sides := 8) -> ArrayMesh:
	var rings: Array = []
	var ring_n: Array = []
	for k in seg + 1:
		var t := float(k) / seg
		var pos := p0 * (1.0 - t) * (1.0 - t) + p1 * 2.0 * (1.0 - t) * t + p2 * t * t
		var tan := ((p1 - p0) * 2.0 * (1.0 - t) + (p2 - p1) * 2.0 * t).normalized()
		var out := pos - center
		var nrm := (out - tan * out.dot(tan)).normalized()
		var bin := tan.cross(nrm).normalized()
		# Full width near the root, tapering to a point at the tip.
		var taper := pow(1.0 - t, 0.75) * lerpf(0.75, 1.0, smoothstep(0.0, 0.25, t))
		var ring: Array[Vector3] = []
		var norms: Array[Vector3] = []
		for s in sides + 1:
			var th := TAU * s / sides
			ring.append(pos + bin * cos(th) * width * taper + nrm * sin(th) * thick * taper)
			norms.append((bin * cos(th) / width + nrm * sin(th) / thick).normalized())
		rings.append(ring)
		ring_n.append(norms)

	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for k in seg:
		for s in sides:
			var p := [rings[k][s], rings[k][s + 1], rings[k + 1][s], rings[k + 1][s + 1]]
			var n := [ring_n[k][s], ring_n[k][s + 1], ring_n[k + 1][s], ring_n[k + 1][s + 1]]
			var uv := [Vector2(float(s) / sides, float(k) / seg), Vector2(float(s + 1) / sides, float(k) / seg),
				Vector2(float(s) / sides, float(k + 1) / seg), Vector2(float(s + 1) / sides, float(k + 1) / seg)]
			var expected: Vector3 = (n[0] + n[3]).normalized()
			_tri(st, [p[0], p[1], p[3]], [n[0], n[1], n[3]], [uv[0], uv[1], uv[3]], expected)
			_tri(st, [p[0], p[3], p[2]], [n[0], n[3], n[2]], [uv[0], uv[3], uv[2]], expected)
	return st.commit()
