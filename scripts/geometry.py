"""Pure Python geometry in metres. No Blender dependency; testable with unittest."""
from math import atan2, cos, pi, sin


def pointed_arch(half_width, rise, segments=32):
    """Two tangent-at-spring circular arcs meeting at a pointed crown, left to right."""
    if half_width <= 0 or rise <= 0 or segments < 2:
        raise ValueError("Arch width/rise must be positive; use at least two segments")
    center = (rise * rise - half_width * half_width) / (2 * half_width)
    radius = half_width + center
    end = atan2(rise, -center)
    left = [(center + radius * cos(pi + (end - pi) * i / segments),
             radius * sin(pi + (end - pi) * i / segments))
            for i in range(segments + 1)]
    return left + [(-x, z) for x, z in reversed(left[:-1])]


def layout(config):
    n = config['river_spans']
    if n < 1 or config['length'] <= 2 * config['end_margin']:
        raise ValueError('Invalid span layout')
    pitch = (config['length'] - 2 * config['end_margin']) / n
    if config['lower_opening'] >= pitch:
        raise ValueError('Openings must leave positive pier thickness')
    centers = [(i - (n - 1) / 2) * pitch for i in range(n)]
    return pitch, centers


class MeshBuffer:
    def __init__(self):
        self.vertices, self.faces, self.materials = [], [], []

    def poly(self, vertices, faces, material=0):
        offset = len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.extend(tuple(v + offset for v in face) for face in faces)
        self.materials.extend([material] * len(faces))

    def box(self, center, size, material=0):
        x, y, z = center
        a, b, c = (v / 2 for v in size)
        self.poly([(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
                   (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)],
                  [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)], material)

    def prism(self, polygon, y0, y1, material=0):
        """Extrude a counterclockwise XZ polygon through Y."""
        n = len(polygon)
        vertices = [(x, y0, z) for x,z in polygon] + [(x, y1, z) for x,z in polygon]
        faces = [tuple(range(n)), tuple(reversed(range(n,2*n)))]
        faces += [(i, i+n, (i+1)%n+n, (i+1)%n) for i in range(n)]
        self.poly(vertices, faces, material)

    def arch_wall(self, x, y, width, opening, base, spring, rise, top, depth, segments=32):
        """Solid wall with a real open arch, assembled without boolean modifiers."""
        a = opening / 2
        pier = (width - opening) / 2
        if pier > 1e-6:
            for side in (-1,1):
                self.box((x + side*(a + pier/2), y, (base+top)/2), (pier,depth,top-base))
        curve = pointed_arch(a, rise, segments)
        # One closed spandrel volume; avoid coplanar internal faces between wedges.
        polygon = [(x+u,spring+v) for u,v in curve] + [(x+a,top),(x-a,top)]
        self.prism(polygon, y-depth/2, y+depth/2)

    def arch_ring(self, x, y, opening, spring, rise, thickness, depth, segments=32,
                  palette=1, gap=0.035):
        inner = pointed_arch(opening/2, rise, segments)
        outer = pointed_arch(opening/2+thickness, rise+thickness, segments)
        for i in range(len(inner)-1):
            # Independent voussoirs expose actual mortar joints and catch grazing light.
            def lerp(a,b,t): return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)
            p = [lerp(inner[i],inner[i+1],gap),lerp(inner[i],inner[i+1],1-gap),
                 lerp(outer[i],outer[i+1],1-gap),lerp(outer[i],outer[i+1],gap)]
            self.prism([(x+u,spring+v) for u,v in p],y-depth/2,y+depth/2,i%palette)

    def crossed_vault(self, x, opening, width, spring, rise, top,
                      passage_width=2.05, passage_spring=2.75, passage_rise=1.55,
                      segments=40):
        """Closed spandrel above intersecting river and longitudinal pointed vaults.

        The underside is the maximum of both opening profiles. This preserves the
        union of the voids, including headroom at the river-vault spring lines.
        """
        xs=pointed_arch(opening/2,rise,segments)
        ys=[(-width/2,0),(-passage_width/2-.005,0)]+pointed_arch(passage_width/2,passage_rise,16)+[(passage_width/2+.005,0),(width/2,0)]
        nx,ny=len(xs),len(ys)
        bottom=[]
        for j,(y,pz) in enumerate(ys):
            for u,rz in xs:
                underside=spring+rz
                if 1<j<ny-2:
                    underside=max(underside,passage_spring+pz)
                if underside>=top: raise ValueError('Vault crown must remain below the deck')
                bottom.append((x+u,y,underside))
        n=len(bottom)
        vertices=bottom+[(u,v,top) for u,v,z in bottom]
        faces=[]
        for j in range(ny-1):
            for i in range(nx-1):
                a=j*nx+i
                faces.append((a,a+nx,a+nx+1,a+1))
                faces.append((a+n,a+1+n,a+nx+1+n,a+nx+n))
        for i in range(nx-1):
            a=i; faces.append((a,a+1,a+1+n,a+n))
            a=(ny-1)*nx+i; faces.append((a+1,a,a+n,a+1+n))
        for j in range(ny-1):
            a=j*nx; faces.append((a+nx,a,a+n,a+nx+n))
            a=j*nx+nx-1; faces.append((a,a+nx,a+nx+n,a+n))
        self.poly(vertices,faces)
