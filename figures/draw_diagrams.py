"""Vector drawing primitives; copied into each independent project generator."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

plt.rcParams.update({'font.family':'STIXGeneral', 'mathtext.fontset':'stix',
                     'font.size':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'text.usetex':False, 'axes.unicode_minus':False})
CM = 1 / 2.54

class Drawing:
    def __init__(self, bounds):
        x0,y0,x1,y1 = bounds
        self.fig = plt.figure(figsize=((x1-x0)*CM,(y1-y0)*CM))
        self.ax = self.fig.add_axes([0,0,1,1], xlim=(x0,x1), ylim=(y0,y1))
        self.ax.set_aspect('equal'); self.ax.axis('off')
        self.nodes = {}
        self.labels = []

    def text(self,x,y,label,size=9,ha='center',va='center'):
        artist=self.ax.text(x,y,label,fontsize=size,ha=ha,va=va,
                            linespacing=1.15,clip_on=False,zorder=4)
        self.labels.append([artist,None])
        return artist

    def box(self,name,x,y,w,h,label,dashed=False,shape='rect',size=9):
        style = {'edgecolor':'black','facecolor':'white','linewidth':.55,
                 'linestyle':(0,(4,3)) if dashed else 'solid', 'zorder':2}
        if shape == 'diamond':
            obj = Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],**style)
        elif shape == 'circle': obj = Circle((x,y),w/2,**style)
        else: obj = Rectangle((x-w/2,y-h/2),w,h,**style)
        self.ax.add_patch(obj); self.text(x,y,label,size)
        self.labels[-1][1]=(x-w/2,y-h/2,x+w/2,y+h/2)
        self.nodes[name] = (x,y,w,h,shape)

    def point(self,name,side):
        x,y,w,h,_ = self.nodes[name]
        return {'n':(x,y+h/2),'s':(x,y-h/2),'e':(x+w/2,y),
                'w':(x-w/2,y),'nw':(x-w/2,y+h/2),
                'ne':(x+w/2,y+h/2),'c':(x,y)}[side]

    def line(self,points,dashed=False):
        xs,ys=zip(*points)
        self.ax.plot(xs,ys,color='black',linewidth=.55,
                     linestyle=(0,(4,3)) if dashed else 'solid',zorder=1)

    def arrow(self,p,q,dashed=False,via=()):
        points=[p,*via,q]
        if via:self.line(points[:-1],dashed)
        self.ax.add_patch(FancyArrowPatch(points[-2],points[-1],
                         arrowstyle='-|>',mutation_scale=7.5,linewidth=.55,
                         color='black',shrinkA=0,shrinkB=0,
                         linestyle=(0,(4,3)) if dashed else 'solid',zorder=1))

    def edge(self,a,b,sa='s',sb='n',**kwargs):
        self.arrow(self.point(a,sa),self.point(b,sb),**kwargs)

    def frame(self,x,y,w,h):
        self.ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='black',
                                   linewidth=.55,linestyle=(0,(4,3)),zorder=0))

    def save(self,out,name):
        # Fixed physical canvas: do not enlarge or rasterize the scientific figure.
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim()
        for artist,node in self.labels:
            b=artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if b.x0<x0-.02 or b.x1>x1+.02 or b.y0<y0-.02 or b.y1>y1+.02:
                raise ValueError(name+': clipped label '+repr(artist.get_text()))
            if node and (b.x0<node[0]-.02 or b.x1>node[2]+.02 or b.y0<node[1]-.02 or b.y1>node[3]+.02):
                raise ValueError(name+': label exceeds node '+repr(artist.get_text()))
        self.fig.savefig(out/(name+'.pdf'),format='pdf',
                         metadata={'Creator':'Python Matplotlib','Producer':None,
                                   'CreationDate':None,'ModDate':None})
        plt.close(self.fig)

def figures(out):
    d=Drawing((-5.5,-.6,5.5,5.8))
    d.box('f',0,5,3.6,1.05,'Flexible credit $f$\n$E(f)=\\{0,1\\}$')
    for suffix,x,bank,free in [('a',-3.2,0,1),('b',3.2,1,0)]:
        d.box(suffix,x,2.9,2.8,1.0,f'$f\\mapsto b_{bank}$\n$b_{free}$ free')
        d.box(suffix+'x',x,.6,3.8,1.05,f'Request pinned to $b_{bank}$\nno legal extension')
        d.edge('f',suffix);d.text(x,4.12,'choose slot',8)
        d.edge(suffix,suffix+'x');d.text(x+.18,1.72,'later input',8,ha='left')
    d.edge('a','b',sa='e',sb='w',dashed=True)
    d.edge('b','a',sa='w',sb='e',dashed=True)
    d.text(0,3.32,'move $f$',8);d.text(0,2.48,'forbidden',8)
    d.save(out,'persistent-fork')

    d=Drawing((-.6,-2.8,11.6,3.0))
    for name,x,y in [('a',2,2.2),('b',2,-1.2),('da',7,2.2),('db',10,2.2)]:
        d.box(name,x,y,1.05,.65,'$A$' if name in ('a','da') else '$B$')
    for k,x in enumerate([.4,2,3.6]):
        name='s'+str(k);d.box(name,x,.5,.9,.65,f'$b_{k}$')
        d.edge('a',name);d.edge('b',name,sa='n',sb='s')
    for own,x in [('da',7),('db',10)]:
        for k,dx in enumerate([-.65,.65]):
            name=own+str(k);d.box(name,x+dx,.5,.9,.65,f'$b_{k}$')
            d.edge(own,name)
    d.line([(5,-2.5),(5,2.8)],dashed=True)
    d.text(2,-2.25,'Shared: 3 slots\neach request enables one pair',8.5)
    d.text(8.5,-2.25,'Dedicated: 4 slots\ntwo permanently owned per tenant',8.5)
    d.save(out,'shared-capacity')

    d=Drawing((-.1,-1.2,14.9,4.7))
    xs=[1.6,7.4,13.2]
    for k,(x,logical,physical) in enumerate(zip(xs,
            ['$q$\nbefore sampling','$q^{\\mathrm{s}}$\nsampled live set',"$q'$\nafter service"],
            ['$(q,\\mu)$','$(q^{\\mathrm{s}},\\mu^{\\mathrm{s}})$',"$(q',\\mu')$"])):
        d.box('q'+str(k),x,3.6,3.05,1.05,logical)
        d.box('s'+str(k),x,.8,3.05,1.05,physical)
        d.edge('s'+str(k),'q'+str(k),sa='n',sb='s')
        d.text(x+.18,2.2,'projection',8,ha='left')
    for k,txt,low in [(0,'own inputs','acquire; retain survivors'),(1,'public grant','advance or release')]:
        d.edge('q'+str(k),'q'+str(k+1),sa='e',sb='w')
        d.edge('s'+str(k),'s'+str(k+1),sa='e',sb='w')
        d.text((xs[k]+xs[k+1])/2,4.22,txt,8)
        d.text((xs[k]+xs[k+1])/2,-.25,low,8)
    d.save(out,'refinement')


def check():
    # Exact language-level instance represented by the shared-capacity diagram.
    import itertools, tempfile
    pooled=min(sum(c) for c in itertools.product(range(3),repeat=3)
               if all(sum(c[i] for i in E)>=2 for E in itertools.combinations(range(3),2)))
    if pooled!=3 or 2*(3-2+1)!=4:
        raise ValueError('shared/dedicated capacity illustration disagrees')
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        for path in (Path(a),Path(b)): figures(path)
        for name in ('persistent-fork','shared-capacity','refinement'):
            if (Path(a)/(name+'.pdf')).read_bytes()!=(Path(b)/(name+'.pdf')).read_bytes():
                raise ValueError('nondeterministic export: '+name)
    print('Three vector diagrams: exact capacity example, bounds, fresh-export identity passed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Draw the persistent-credit manuscript diagrams directly as embedded-font vectors.')
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.check: check()
    else:
        args.output_dir.mkdir(parents=True,exist_ok=True)
        figures(args.output_dir)

