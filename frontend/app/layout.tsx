import './globals.css';
export const metadata={title:'TrafficSMS',description:'Localized traffic intelligence by SMS'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body><main className="wrap"><nav className="nav"><strong>TrafficSMS</strong><a href="/pricing">Pricing</a></nav>{children}</main></body></html>}
