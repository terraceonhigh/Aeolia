class_name Atmosphere
extends MeshInstance3D

## Atmosphere haze matching JSX reference:
##   new THREE.Mesh(
##     new THREE.IcosahedronGeometry(R*1.02, 3),
##     new THREE.MeshBasicMaterial({color:0x3366aa, transparent:true, opacity:0.03, side:THREE.BackSide})
##   )
##
## BackSide ≡ cull_front: renders only the inner face of the sphere.
## From outside, this is only visible at the limb (globe edge), creating
## a subtle blue atmospheric haze. Flat opacity 0.03 — very subtle.

# R*1.02 where R=1 in Godot
const ATMOSPHERE_RADIUS: float = 1.02
const SPHERE_RINGS: int = 32
const SPHERE_RADIAL_SEGMENTS: int = 32


## Creates the atmosphere sphere mesh matching JSX flat-opacity BackSide mesh.
func setup() -> void:
	var sphere_mesh := SphereMesh.new()
	sphere_mesh.radius = ATMOSPHERE_RADIUS
	sphere_mesh.height = ATMOSPHERE_RADIUS * 2.0
	sphere_mesh.radial_segments = SPHERE_RADIAL_SEGMENTS
	sphere_mesh.rings = SPHERE_RINGS
	mesh = sphere_mesh

	var material := ShaderMaterial.new()
	material.shader = _create_atmosphere_shader()
	# JSX: color 0x3366aa = rgb(0.2, 0.4, 0.667), opacity 0.03
	material.set_shader_parameter("atmosphere_color", Vector3(0.2, 0.4, 0.667))
	material.set_shader_parameter("opacity", 0.03)

	set_surface_override_material(0, material)
	print("Atmosphere: radius=%.3f, opacity=0.03 (BackSide flat, matches JSX)" % ATMOSPHERE_RADIUS)


## Flat-opacity BackSide shader — matches THREE.js MeshBasicMaterial BackSide behavior.
## cull_front renders only the inner sphere face (visible from outside at the limb).
## No Fresnel — pure flat alpha to match JSX exactly.
func _create_atmosphere_shader() -> Shader:
	var shader_code = """
shader_type spatial;
render_mode unshaded, blend_mix, cull_front;

uniform vec3 atmosphere_color : source_color = vec3(0.2, 0.4, 0.667);
uniform float opacity : hint_range(0.0, 1.0) = 0.03;

void fragment() {
	ALBEDO = atmosphere_color;
	ALPHA = opacity;
}
"""
	var shader := Shader.new()
	shader.code = shader_code
	return shader
