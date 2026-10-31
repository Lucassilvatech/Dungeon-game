/** CPU WebGL emulators are slower than Canvas for this sprite-only scene. */
export function softwareRenderer(name:string):boolean{return /swiftshader|llvmpipe|softpipe|software|basic render/i.test(name);}
