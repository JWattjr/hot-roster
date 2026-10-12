import type {Metadata} from 'next';
import '@fontsource/barlow-condensed/600.css';
import '@fontsource/barlow-condensed/700.css';
import '@fontsource/dm-sans/400.css';
import '@fontsource/dm-sans/500.css';
import '@fontsource/dm-sans/700.css';
import './globals.css';
export const metadata:Metadata={title:'Hot Roster · Draft songs. Run the charts.',description:'Fantasy football for the Billboard charts, refereed by GenLayer. A real music league with validator-judged moments and disputes.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
