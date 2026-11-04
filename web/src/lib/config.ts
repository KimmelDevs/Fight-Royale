// Public Supabase settings. The anon key is meant to be public (it ships in the browser
// bundle); Row Level Security and the server functions protect the data. Env vars override.
export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://vyubpbffiwgepkguuypm.supabase.co";
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5dWJwYmZmaXdnZXBrZ3V1eXBtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTM3MjM2NjEsImV4cCI6MjEwOTI5OTY2MX0.iKxNFjhl6GcNVamg3SdQdCU8eZzTaM1bsmuvRgnOmCM";
