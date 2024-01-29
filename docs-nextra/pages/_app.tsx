import { AppProps } from "next/app";
import './styles.css'

export default function InfrahubDocs({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />
}
