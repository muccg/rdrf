import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';


declare global {
    interface Window {
          dontcare: string;
	
    }
};



export function testts(s: string) {
       return "You typed " + s;
}










