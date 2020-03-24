//Used .cpp extension to get nice syntax highlighting 
//Code to perform T1 like measurements
//_samplesparam_ should be used to specify the number of points in the waveforms
//Wait time can be set either here or by formatting the string

const NumSamples = _NumSamples_;
const waitInc    = _waitInc_;
const clearTime  = _clearTime_;
const markerPos  = _markerPos_;

wave w1   = ones(NumSamples);
wave w2   = zeros(NumSamples);
wave markL = marker(markerPos,0);
wave markR = marker(NumSamples-markerPos,1);
wave mark  = join(markL,markR);
wave w1m  = w1 + mark; //Add markers to waveform to trigger digitizer

for(var i=1; i<5;i=i+1){
    playWave(w1m,w2);
    waitWave(); //Wait until the end of playback to continue to the next command
    wait(waitInc*i); //Sets the amount of time between the two pulses (is multiples of sequencer clock, around 3.3 ns)
    playWave(w2,w1m);
    waitWave();
    wait(clearTime);
}