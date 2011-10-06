#ifndef adderror
    #define adderror( b, e ) ( ((b) < -(e)) ? 0x00 : ( ((0xFF - (b)) < (e)) ? 0xFF : (b + e) ) )
#endif