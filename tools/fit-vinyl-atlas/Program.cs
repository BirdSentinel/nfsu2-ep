// Reproject indexed vinyl mipmaps; preserve palette, names, hashes and metadata.
// Arguments: source pack, target pack, 512x512 float2 map, Binarius directory.
using System.Reflection;
using System.Runtime.InteropServices;
if(args.Length!=4)throw new ArgumentException("Expected source, destination, map and Binarius directory");
var dir=Path.GetFullPath(args[3]);
AppDomain.CurrentDomain.AssemblyResolve+=(_,e)=>Assembly.LoadFrom(Path.Combine(dir,new AssemblyName(e.Name).Name+".dll"));
NativeLibrary.Load(Path.Combine(dir,"LZCompressLib.dll"));
var lib=Assembly.LoadFrom(Path.Combine(dir,"Nikki.dll"));
var type=lib.GetType("Nikki.Utils.Interop");
var enumType=lib.GetType("Nikki.Reflection.Enum.LZCompressionType");
var decode=type.GetMethod("Decompress",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static);
var encode=type.GetMethod("Compress",new Type[]{typeof(byte[]),enumType});
var codec=Enum.Parse(enumType,"JDLZ");
var data=File.ReadAllBytes(args[0]);var mapBytes=File.ReadAllBytes(args[2]);
if(mapBytes.Length!=512*512*8)throw new InvalidDataException("Invalid UV map");
var map=new float[512*512*2];Buffer.BlockCopy(mapBytes,0,map,0,mapBytes.Length);
int U(int p)=>BitConverter.ToInt32(data,p);
var slots=new List<int>();int dataChunk=-1, imageChunk=-1;
for(int p=8;p<data.Length;){int tag=U(p),size=U(p+4);
 if(tag==unchecked((int)0xb3310000))for(int q=p+8;q<p+8+size;q+=8+U(q+4))
  if(U(q)==0x33310003)for(int e=q+8;e<q+8+U(q+4);e+=24)slots.Add(e);
 if(tag==unchecked((int)0xb3320000)){
  dataChunk=p;
  for(int q=p+8;q<p+8+size;q+=8+U(q+4))if(U(q)==0x33320002)imageChunk=q;
 }
 p+=8+size;
}
if(slots.Count==0||dataChunk<0||imageChunk<0)throw new InvalidDataException("Missing TPK tables");
int start=slots.Min(e=>U(e+4));
using var output=new MemoryStream();output.Write(data,0,start);
void Patch(int p,int v){long save=output.Position;output.Position=p;output.Write(BitConverter.GetBytes(v));output.Position=save;}
int converted=0;
foreach(int e in slots){
 var raw=(byte[])decode.Invoke(null,new object[]{data.AsSpan(U(e+4),U(e+8)).ToArray()});
 int ti=raw.Length-156;
 if(raw.Length!=350748 && raw.Length!=350684)throw new InvalidDataException("Unexpected vinyl allocation");
 if(BitConverter.ToUInt16(raw,ti+0x44)!=512 || BitConverter.ToUInt16(raw,ti+0x46)!=512 || raw[ti+0x4e]!=7)throw new InvalidDataException("Unexpected vinyl dimensions");
 var before=(byte[])raw.Clone();
 int offset=0;
 for(int level=0;level<7;level++){
  int width=512>>level;var frequencies=new int[256];
  for(int i=0;i<width*width;i++)frequencies[before[offset+i]]++;
  byte empty=(byte)Array.IndexOf(frequencies,frequencies.Max());
  for(int y=0;y<width;y++)for(int x=0;x<width;x++){
   int fullX=Math.Min(511,(x<<level)+(1<<level)/2),fullY=Math.Min(511,(y<<level)+(1<<level)/2);
   int at=(fullY*512+fullX)*2;float u=map[at],v=map[at+1];
   raw[offset+y*width+x]=float.IsFinite(u)&&float.IsFinite(v)&&u>=0&&u<1&&v>=0&&v<1
    ?before[offset+Math.Clamp((int)(v*width),0,width-1)*width+Math.Clamp((int)(u*width),0,width-1)]:empty;
  }
  offset+=width*width;
 }
 if(!before.AsSpan(349504).SequenceEqual(raw.AsSpan(349504)))throw new Exception("Metadata changed");
 var packed=(byte[])encode.Invoke(null,new object[]{raw,codec});
 var verified=(byte[])decode.Invoke(null,new object[]{packed});
 if(!raw.AsSpan().SequenceEqual(verified))throw new Exception("Codec round trip failed");
 while(output.Position%128!=0)output.WriteByte(0);
 Patch(e+4,(int)output.Position);Patch(e+8,packed.Length);Patch(e+12,raw.Length);
 output.Write(packed);converted++;
 if(converted%100==0)Console.WriteLine($"Fitted and verified {converted}/{slots.Count} vinyl textures");
}
Patch(4,(int)output.Length-8);Patch(dataChunk+4,(int)output.Length-dataChunk-8);
// PNG discovery walks the entire TPK, including this inner image payload.
// Leaving its old length makes the next compressed bytes look like a chunk.
Patch(imageChunk+4,(int)output.Length-imageChunk-8);
var result=output.ToArray();
void ValidateChunks(int begin,int end){
 for(int p=begin;p<end;){
  if(end-p<8)throw new InvalidDataException("Truncated archive header");
  uint tag=BitConverter.ToUInt32(result,p),size=BitConverter.ToUInt32(result,p+4);
  long next=(long)p+8+size;
  if(next>end)throw new InvalidDataException("Truncated archive chunk");
  if((tag&0x80000000)!=0)ValidateChunks(p+8,(int)next);
  p=(int)next;
 }
}
ValidateChunks(0,result.Length);
File.WriteAllBytes(args[1],result);
Console.WriteLine($"PASS {converted} vinyl textures and masks; all palette/metadata bytes preserved");
