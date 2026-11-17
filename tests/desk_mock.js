/* Minimal deterministic DOM stub: does not claim to test browser layout. */
const elements=Object.create(null);
const document={getElementById(id){
  if(!elements[id]) elements[id]={value:'',textContent:'',disabled:false,children:[],listeners:{},classList:{toggle(){}},append(x){this.children.push(x);},addEventListener(k,f){this.listeners[k]=f;}};
  return elements[id];
},createElement(){return {value:'',textContent:'',click(){}};}};
const window={addEventListener(){},confirm(){return true;}};
