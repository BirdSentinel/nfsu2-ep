// Append NB rear and 240SX front lamps without changing saved-part indices.
using System.Reflection;
using System.Text.RegularExpressions;
using Endscript.Core;
using Endscript.Profiles;
using UG2 = Nikki.Support.Underground2;

var libraries=Path.GetFullPath(args[2]);
AppDomain.CurrentDomain.AssemblyResolve += (_,e) => Assembly.LoadFrom(Path.Combine(libraries,new AssemblyName(e.Name).Name+".dll"));
System.Runtime.InteropServices.NativeLibrary.Load(Path.Combine(libraries,"LZCompressLib.dll"));
Run(args[0],args[1],libraries);

static void Run(string launcher,string game,string libraries)
{
    Underground2Profile.MainHashList=Path.Combine(libraries,"mainkeys/underground2.txt");
    Underground2Profile.CustomHashList=Path.Combine(libraries,"userkeys/underground2.txt");
    Nikki.Core.Map.CustomAttribFile=Path.Combine(libraries,"userkeys/CustomAttributes.txt");
    Launch.Deserialize(launcher,out var launch);
    launch.ThisDir=Path.GetDirectoryName(Path.GetFullPath(launcher));launch.Directory=game;
    var profile=BaseProfile.NewProfile(launch.GameID,game);
    foreach(var error in profile.Load(launch))throw new Exception(error.ToString());
    var db=profile[@"GLOBAL\GLOBALB.LZC"].Database;
    var models=(System.Collections.IEnumerable)db.GetManager("DBModelParts");
    var all=models.Cast<UG2.Class.DBModelPart>().ToList();
    var source=all.Single(m=>m.CollectionName=="MIATA");
    var target=all.Single(m=>m.CollectionName=="MX5NA");
    for(int style=1;style<=14;style++)
    {
        int destination=style==1?15:style; // STYLE01 remains the legacy EDOLIX rack.
        string label=$"MX5NA_STYLE{destination:00}_BRAKELIGHT";
        if(target.ModelCarParts.Cast<UG2.Parts.CarParts.RealCarPart>().Any(p=>p.PartLabel==label))continue;
        var original=(UG2.Parts.CarParts.RealCarPart)source.ModelCarParts.Cast<UG2.Parts.CarParts.RealCarPart>().Single(p=>p.PartLabel==$"MIATA_STYLE{style:00}_BRAKELIGHT");
        var part=(UG2.Parts.CarParts.RealCarPart)original.PlainCopy();
        part.Model=target;
        part.MakeReplace(false,"^MIATA","MX5NA",RegexOptions.None);
        if(style==1)
        {
            part.MakeReplace(false,"^MX5NA_STYLE01","MX5NA_STYLE15",RegexOptions.None);
            part.LodStruct.Concatenator="_STYLE15";
        }
        part.PartLabel=label;
        target.ModelCarParts.Add(part);
        Console.WriteLine("Added "+label);
    }
    var popupDonor=all.Single(m=>m.CollectionName=="240SX");
    foreach(var original in popupDonor.ModelCarParts.Cast<UG2.Parts.CarParts.RealCarPart>()
        .Where(p=>Regex.IsMatch(p.PartLabel,@"^240SX_STYLE\d\d_HEADLIGHT$")))
    {
        string label=Regex.Replace(original.PartLabel,"^240SX","MX5NA");
        if(target.ModelCarParts.Cast<UG2.Parts.CarParts.RealCarPart>().Any(p=>p.PartLabel==label))continue;
        var part=(UG2.Parts.CarParts.RealCarPart)original.PlainCopy();
        part.Model=target;
        part.MakeReplace(false,"^240SX","MX5NA",RegexOptions.None);
        part.PartLabel=label;
        target.ModelCarParts.Add(part);
        Console.WriteLine("Added "+label);
    }
    foreach(var error in profile.Save())throw new Exception(error.ToString());
}




