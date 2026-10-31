pub mod provisioning {
    include!(concat!(env!("OUT_DIR"), "/provisioning.rs"));
}
pub mod core {
    pub use crate::provisioning;
}
#[path = "../overlay/src/android/proot/arch_fs.rs"]
pub mod arch_fs;
#[path = "../overlay/src/android/proot/arch_gpu.rs"]
pub mod arch_gpu;

#[cfg(test)]
mod contracts;
